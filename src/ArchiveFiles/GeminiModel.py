from dotenv import load_dotenv
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma

# Load variables from .env into environment
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    api_key=api_key
)

response = llm.stream("Hello! How are you?")

for chunk in response:
    print(chunk.content, end="", flush=True)


