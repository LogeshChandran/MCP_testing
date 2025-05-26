import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import AgentExecutor#, create_react_agent # Changed import
# from langchain_community.chat_models import ChatOllama # Changed import
from langchain_ollama import ChatOllama
from langchain import hub
# from langchain.prompts import PromptTemplate  # Removed
from langchain.tools import Tool # Import Tool
from langgraph.prebuilt import create_react_agent

async def main():
    try:
        print("Started...")
        client = MultiServerMCPClient(
            {
                "math": {
                    "command": "python",
                    # REPLACE WITH THE FULL ABSOLUTE PATH
                    "args": ["math_server.py"],
                    "transport": "stdio",
                },
                "weather": {
                    # make sure you start your weather server on port 8000
                    "url": "http://localhost:8000/mcp",
                    "transport": "streamable_http",
                }
            }
        )
        print("2. Started...")
        tools = await client.get_tools()
        print("3. Started...")
        # print("Tools:", tools)

        # Create ChatOllama instance
        model = ChatOllama(model="llama3.2:3b")  #  Using ChatOllama


        # Get the ReAct prompt from LangChain Hub
        prompt = hub.pull("hwchase17/react")


        # Convert tools to LangChain Tool objects
        langchain_tools = [
            Tool(
                name=tool.name,
                func=tool.invoke,  # Assuming tool.invoke is the correct method
                description=tool.description,
            )
            for tool in tools
        ]

        # Create ReAct agent
        agent = create_react_agent(model, tools=tools)  # Changed


        agent_executor = AgentExecutor(agent=agent, tools=tools)

        math_response = await agent.ainvoke({"messages": "what's (3 + 5) x 12?"})
        print("Math Response:", math_response["messages"])

        weather_response = await agent_executor.ainvoke({"input": "what is the weather in nyc?"})
        print("Weather Response:", weather_response)

    except Exception as e:
        print(f"An error occurred: {e}")

# Run the async function
if __name__ == "__main__":
    asyncio.run(main())
