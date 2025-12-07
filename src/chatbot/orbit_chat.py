"""
OrbitMeetAI Chatbot - RAG-based chatbot using MongoDB Vector Search and Voyage AI embeddings.
Uses meeting transcripts from MongoDB to provide context-aware answers.
"""
import os
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId
import certifi
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from loguru import logger
import requests
import numpy as np

load_dotenv()

# ======================================================================
# LOGGER CONFIGURATION
# ======================================================================
logger.remove()  # remove default
logger.add(
    sink=lambda msg: print(msg, end=""),
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
           "<level>{level}</level> | "
           "<cyan>{message}</cyan>"
)

# ======================================================================
# GLOBAL STATE
# ======================================================================
mongo_uri = os.getenv("MONGO_URI")
voyage_api_key = os.getenv("VOYAGE_API_KEY")
chatbot_instances: Dict[str, Any] = {}  # Cache chatbot instances by project_id


# ======================================================================
# VOYAGE AI EMBEDDINGS
# ======================================================================
class VoyageEmbeddings:
    """Wrapper for Voyage AI embeddings API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.voyageai.com/v1/embeddings"
        self.model = "voyage-2"  # or "voyage-large-2" for better quality
    
    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a single query"""
        return self.embed_documents([text])[0]
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple documents"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "input": texts,
            "model": self.model
        }
        
        response = requests.post(self.base_url, json=data, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        return [item["embedding"] for item in result["data"]]


# ======================================================================
# MONGODB VECTOR STORE
# ======================================================================
class MongoDBVectorStore:
    """MongoDB-based vector store for transcript embeddings"""
    
    def __init__(self, mongo_uri: str, db_name: str, collection_name: str, embeddings):
        self.client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        self.embeddings = embeddings
    
    def add_documents(self, documents: List[Document], project_id: str):
        """Add documents with embeddings to MongoDB"""
        texts = [doc.page_content for doc in documents]
        embeddings = self.embeddings.embed_documents(texts)
        
        # Prepare documents for MongoDB
        mongo_docs = []
        for doc, embedding in zip(documents, embeddings):
            mongo_doc = {
                "project_id": project_id,
                "text": doc.page_content,
                "embedding": embedding,
                "metadata": doc.metadata,
                "meeting_name": doc.metadata.get("meeting_name", ""),
                "meeting_time": doc.metadata.get("meeting_time", ""),
                "participants": doc.metadata.get("participants", "")
            }
            mongo_docs.append(mongo_doc)
        
        # Insert into MongoDB
        if mongo_docs:
            self.collection.insert_many(mongo_docs)
            logger.info(f"Inserted {len(mongo_docs)} documents into vector store")
    
    def similarity_search(self, query: str, project_id: str, k: int = 5) -> List[Document]:
        """Search for similar documents using vector similarity"""
        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)
        
        # Use MongoDB aggregation pipeline for vector search
        # Note: This requires a vector search index in MongoDB Atlas
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",  # Name of your vector search index
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": k * 10,
                    "limit": k
                }
            },
            {
                "$match": {
                    "project_id": project_id
                }
            },
            {
                "$project": {
                    "text": 1,
                    "metadata": 1,
                    "meeting_name": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]
        
        try:
            results = list(self.collection.aggregate(pipeline))
        except Exception as e:
            # Fallback to cosine similarity if vector search index doesn't exist
            logger.warning(f"Vector search index not found, using cosine similarity: {e}")
            results = self._cosine_similarity_search(query_embedding, project_id, k)
        
        # Convert to LangChain Documents
        documents = []
        for result in results:
            doc = Document(
                page_content=result["text"],
                metadata={
                    **result.get("metadata", {}),
                    "meeting_name": result.get("meeting_name", ""),
                    "score": result.get("score", 0.0)
                }
            )
            documents.append(doc)
        
        return documents
    
    def _cosine_similarity_search(self, query_embedding: List[float], project_id: str, k: int) -> List[Dict]:
        """Fallback: Manual cosine similarity search"""
        # Fetch all documents for the project
        all_docs = list(self.collection.find({"project_id": project_id}))
        
        if not all_docs:
            return []
        
        # Calculate cosine similarity
        query_vec = np.array(query_embedding)
        similarities = []
        
        for doc in all_docs:
            doc_vec = np.array(doc.get("embedding", []))
            if len(doc_vec) > 0:
                # Cosine similarity
                similarity = np.dot(query_vec, doc_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(doc_vec))
                similarities.append((similarity, doc))
        
        # Sort by similarity and return top k
        similarities.sort(key=lambda x: x[0], reverse=True)
        return [{"text": doc["text"], "metadata": doc.get("metadata", {}), 
                "meeting_name": doc.get("meeting_name", ""), "score": sim} 
                for sim, doc in similarities[:k]]


# ======================================================================
# FETCH MEETING TRANSCRIPTS FROM MONGODB
# ======================================================================
def fetch_project_transcripts(project_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all meeting transcripts for a given project_id from MongoDB.
    
    Args:
        project_id: MongoDB ObjectId as string
        
    Returns:
        List of meeting documents with transcripts
    """
    if not mongo_uri:
        raise ValueError("MONGO_URI not configured")
    
    try:
        # Validate ObjectId
        try:
            object_id = ObjectId(project_id)
        except InvalidId:
            raise ValueError(f"Invalid ObjectId format: {project_id}")
        
        # Connect to MongoDB
        client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
        db = client["OMNI_MEET_DB"]
        collection = db["Raw_Transcripts"]
        
        # Fetch document
        doc = collection.find_one({"_id": object_id})
        
        if not doc:
            raise ValueError(f"Project with id '{project_id}' not found")
        
        project_name = doc.get("Project_name", "Unknown Project")
        meetings = doc.get("meetings", [])
        
        # Extract transcripts
        meeting_data = []
        for meeting in meetings:
            meeting_name = meeting.get("meeting_name", "Unknown Meeting")
            meeting_time = meeting.get("meeting_time", "")
            participants = meeting.get("participants", [])
            transcript_list = meeting.get("Transcript", [])
            
            # Get transcript text (first element if list, or the value itself)
            transcript_text = ""
            if transcript_list:
                if isinstance(transcript_list, list):
                    transcript_text = transcript_list[0] if transcript_list else ""
                else:
                    transcript_text = str(transcript_list)
            
            if transcript_text:
                meeting_data.append({
                    "meeting_name": meeting_name,
                    "meeting_time": meeting_time,
                    "participants": participants,
                    "transcript": transcript_text
                })
        
        logger.info(f"Fetched {len(meeting_data)} meetings for project '{project_name}'")
        return meeting_data
    
    except Exception as e:
        logger.error(f"Error fetching transcripts: {e}")
        raise


# ======================================================================
# CREATE VECTOR STORE FROM TRANSCRIPTS
# ======================================================================
def create_vector_store(meetings: List[Dict[str, Any]], project_id: str) -> MongoDBVectorStore:
    """
    Create a MongoDB vector store from meeting transcripts.
    
    Args:
        meetings: List of meeting dictionaries with transcripts
        project_id: Project ID for unique vector store
        
    Returns:
        MongoDBVectorStore instance
    """
    if not meetings:
        raise ValueError("No meetings found to create vector store")
    
    if not voyage_api_key:
        raise ValueError("VOYAGE_API_KEY not configured")
    
    # Initialize embeddings
    embeddings = VoyageEmbeddings(voyage_api_key)
    
    # Create vector store
    vector_store = MongoDBVectorStore(
        mongo_uri=mongo_uri,
        db_name="OMNI_MEET_DB",
        collection_name="Transcripts_vectorDB",
        embeddings=embeddings
    )
    
    # Check if documents already exist for this project
    existing_count = vector_store.collection.count_documents({"project_id": project_id})
    
    if existing_count > 0:
        logger.info(f"Vector store already exists for project {project_id} with {existing_count} documents")
        return vector_store
    
    # Create documents
    documents = []
    for meeting in meetings:
        # Create a formatted document with metadata
        content = f"""
Meeting: {meeting['meeting_name']}
Time: {meeting['meeting_time']}
Participants: {', '.join(meeting['participants'])}

Transcript:
{meeting['transcript']}
"""
        doc = Document(
            page_content=content,
            metadata={
                "meeting_name": meeting['meeting_name'],
                "meeting_time": meeting['meeting_time'],
                "participants": ', '.join(meeting['participants'])
            }
        )
        documents.append(doc)
    
    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    splits = text_splitter.split_documents(documents)
    
    # Add to MongoDB vector store
    vector_store.add_documents(splits, project_id)
    
    logger.info(f"Created vector store with {len(splits)} chunks for project {project_id}")
    return vector_store


# ======================================================================
# MONGODB RETRIEVER
# ======================================================================
class MongoDBRetriever:
    """LangChain retriever for MongoDB vector store"""
    
    def __init__(self, vector_store: MongoDBVectorStore, project_id: str, k: int = 5):
        self.vector_store = vector_store
        self.project_id = project_id
        self.k = k
    
    def get_relevant_documents(self, query: str) -> List[Document]:
        """Retrieve relevant documents for a query"""
        return self.vector_store.similarity_search(query, self.project_id, self.k)
    
    async def aget_relevant_documents(self, query: str) -> List[Document]:
        """Async version of get_relevant_documents"""
        return self.get_relevant_documents(query)


# ======================================================================
# INITIALIZE CHATBOT
# ======================================================================
def initialize_chatbot(project_id: str, force_refresh: bool = False):
    """
    Initialize or retrieve a chatbot instance for a given project.
    
    Args:
        project_id: MongoDB ObjectId as string
        force_refresh: If True, recreate the vector store even if cached
        
    Returns:
        ConversationalRetrievalChain instance
    """
    # Check cache
    if project_id in chatbot_instances and not force_refresh:
        logger.info(f"Using cached chatbot for project {project_id}")
        return chatbot_instances[project_id]
    
    logger.info(f"Initializing chatbot for project {project_id}")
    
    # Fetch transcripts
    meetings = fetch_project_transcripts(project_id)
    
    if not meetings:
        raise ValueError(f"No meetings found for project {project_id}")
    
    # Create vector store
    vector_store = create_vector_store(meetings, project_id)
    
    # Create retriever
    retriever = MongoDBRetriever(vector_store, project_id, k=5)
    
    # Initialize LLM
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables")
    
    llm = ChatGroq(
        model="openai/gpt-oss-20b",
        temperature=0.3,
        api_key=api_key
    )
    
    # Create memory for conversation
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        output_key="answer"
    )
    
    # Create conversational retrieval chain
    qa_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        return_source_documents=True,
        verbose=False
    )
    
    # Cache the instance
    chatbot_instances[project_id] = qa_chain
    
    logger.success(f"Chatbot initialized for project {project_id}")
    return qa_chain


# ======================================================================
# CHAT FUNCTION
# ======================================================================
async def chat_with_project(project_id: str, question: str, chat_history: Optional[List] = None) -> Dict[str, Any]:
    """
    Chat with the project chatbot.
    
    Args:
        project_id: MongoDB ObjectId as string
        question: User's question
        chat_history: Optional list of previous messages for context
        
    Returns:
        Dictionary with answer and metadata
    """
    try:
        # Initialize chatbot
        qa_chain = initialize_chatbot(project_id)
        
        # Prepare chat history if provided
        if chat_history:
            # Reset memory and add history
            qa_chain.memory.clear()
            for msg in chat_history:
                if msg.get("role") == "user":
                    qa_chain.memory.chat_memory.add_user_message(msg.get("content", ""))
                elif msg.get("role") == "assistant":
                    qa_chain.memory.chat_memory.add_ai_message(msg.get("content", ""))
        
        # Get answer
        result = await qa_chain.ainvoke({"question": question})
        
        # Extract answer and sources
        answer = result.get("answer", "I couldn't generate an answer.")
        source_docs = result.get("source_documents", [])
        
        # Extract source meeting names
        sources = []
        for doc in source_docs:
            metadata = doc.metadata
            if "meeting_name" in metadata:
                sources.append(metadata["meeting_name"])
        
        return {
            "answer": answer,
            "sources": list(set(sources)),  # Remove duplicates
            "project_id": project_id
        }
    
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise


# ======================================================================
# FIND PROJECT BY NAME
# ======================================================================
def find_project_by_name(project_name: str) -> Optional[str]:
    """
    Find project_id (ObjectId) by project name.
    
    Args:
        project_name: Project name to search for
        
    Returns:
        Project ID (ObjectId as string) or None if not found
    """
    if not mongo_uri:
        raise ValueError("MONGO_URI not configured")
    
    try:
        client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
        db = client["OMNI_MEET_DB"]
        collection = db["Raw_Transcripts"]
        
        # Search for project by name (case-insensitive)
        doc = collection.find_one(
            {"Project_name": {"$regex": project_name, "$options": "i"}}
        )
        
        if doc:
            return str(doc["_id"])
        
        return None
    
    except Exception as e:
        logger.error(f"Error finding project: {e}")
        raise

