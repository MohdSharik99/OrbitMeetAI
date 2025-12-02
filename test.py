from typing import List
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langchain_classic.agents import initialize_agent, AgentType
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.tools import Tool
import os

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=api_key,
    temperature=0.7
)


class Source(BaseModel):
    url: str = Field(description="The URL of the source")


class AgentResponse(BaseModel):
    answer: str = Field(description="The agent's answer to the query")
    sources: List[Source] = Field(default_factory=list)


# Create a dummy tool that just returns the input
def dummy_tool(input_text: str) -> str:
    """A dummy tool that returns the input text. Used when no real tools are needed."""
    return f"Processed: {input_text}"


dummy_tool_obj = Tool(
    name="DummyTool",
    func=dummy_tool,
    description="A placeholder tool for when no specific tools are required"
)

tools = [dummy_tool_obj]

# Initialize agent with the dummy tool
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True
)


def main():
    print("Hello from langchain-classic!")

    result = agent.invoke("Hello from langchain-classic! How are you today?")
    print("Result:", result)


if __name__ == "__main__":
    main()