# graph_manager.py
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from typing import List
from langchain_ollama import ChatOllama

class GraphManager:
    """
    Manages the LangGraph agent, MultiServerMCPClient, and tools in a single class.
    """
    def __init__(self, math_server_path: str, weather_server_url: str, model_name: str = "llama3.2:3b"):
        """
        Initializes the GraphManager.

        Args:
            math_server_path (str): The path to the math server script.
            weather_server_url (str): The URL of the weather server.
            model_name (str): The name of the language model to use.
        """
        self.math_server_path = math_server_path
        self.weather_server_url = weather_server_url
        self.model_name = ChatOllama(model=model_name)
        self.client = None
        self.tools = None
        self.agent = None
        self._initialized = False  # Track initialization status

    async def initialize(self):
        """
        Initializes the MultiServerMCPClient, retrieves tools, and creates the agent.
        """
        if not self._initialized:  # Only initialize once
            try:
                await self._initialize_client()
                await self._initialize_tools()
                await self._create_agent()
                self._initialized = True
            except Exception as e:
                print(f"Initialization failed: {e}")
                # Handle initialization failure appropriately (e.g., raise, log)
                raise

    async def _initialize_client(self):
        """
        Initializes the MultiServerMCPClient.
        """
        if self.client is None:
            self.client = MultiServerMCPClient(
                {
                    "math": {
                        "url": self.weather_server_url,
                        "transport": "streamable_http",
                    },
                }
            )

    async def _initialize_tools(self):
        """
        Retrieves the tools from the MultiServerMCPClient.
        """
        if self.client is None:
            await self._initialize_client()
        if self.tools is None:
            self.tools = await self.client.get_tools()

    async def _create_agent(self):
        """
        Creates the LangGraph agent.
        """
        if self.tools is None:
            await self._initialize_tools()
        self.agent = create_react_agent(self.model_name, self.tools)

    async def ainvoke(self, query: str):
        """
        Invokes the agent with the given query.

        Args:
            query (str): The query to pass to the agent.

        Returns:
            The agent's response.
        """
        if not self._initialized:  # Check if initialized before invoking
            await self.initialize()
        response = await self.agent.ainvoke({"messages": [{"role": "user", "content": query}]})
        return response["messages"][-1].content

    async def close(self):
        """
        Closes the MultiServerMCPClient.
        """
        if self.client:
            await self.client.close()
            self.client = None
            self.tools = None
            self.agent = None
            self._initialized = False  # Reset initialization status

# fastapi_app.py
from fastapi import FastAPI
import asyncio
# from graph_manager import GraphManager

app = FastAPI()

MATH_SERVER_PATH = "/path/to/math_server.py"  # Replace with your path
WEATHER_SERVER_URL = "http://localhost:8000/mcp"  # Replace with your server URL

graph_manager = GraphManager(math_server_path=MATH_SERVER_PATH, weather_server_url=WEATHER_SERVER_URL)


async def main():
    math_server_path = "/path/to/math_server.py"  # Replace with the actual path
    weather_server_url = "http://localhost:8000/mcp"  # Replace with the actual URL

    try:
        await graph_manager.initialize()
    except Exception as e:
        print(f"GraphManager initialization failed: {e}")

    # async with GraphCreator(math_server_path=math_server_path, weather_server_url=weather_server_url) as graph_creator:
    #     agent = await graph_creator.create_agent()

        # Assuming create_react_agent returns a Runnable or Chain, not an AgentExecutor directly
        # If it returns an AgentExecutor, you can skip this part
        # agent_executor = AgentExecutor(agent=agent, tools=await graph_creator.client.get_tools())

    math_response = await graph_manager.agent.ainvoke({"messages": [{"role": "user", "content": "what's (3 + 5) x 12?"}]}) # Ensure correct message format
    print("Math Response:", math_response["messages"][-1].content)
    print("Testing")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

# @app.on_event("startup")
# async def startup_event():
#     """
#     Initializes the GraphManager on startup.
#     """
#     await graph_manager.initialize()


# @app.on_event("shutdown")
# async def shutdown_event():
#     """
#     Closes the GraphManager on shutdown.
#     """
#     await graph_manager.close()


# @app.get("/invoke")
# async def invoke_agent(query: str):
#     """
#     Invokes the agent with the given query.
#     """
#     try:
#         response = await graph_manager.ainvoke(query)
#         return {"response": response}
#     except Exception as e:
#         return {"error": str(e)}

# # Example usage:
# # To run: uvicorn fastapi_app:app --reload
