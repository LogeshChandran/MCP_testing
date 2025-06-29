# %%
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

import asyncio
# import uvloop

async def get_playwright_tools():
    # uvloop.install()  # Install uvloop as the default event loop
    # try:
    client = MultiServerMCPClient(
        {
            "play": {
                "command": "npx",
                "args": [
                    "-y",
                    "@executeautomation/playwright-mcp-server"
                ],
                # "url": "http://127.0.0.1:6276/sse",
                "transport": "stdio",
            }
        }
    )
    tools = await client.get_tools()
    print("Tools retrieved successfully:", tools)  # Print tools for verification
    return tools
    # except Exception as e:
    #     print(f"Error retrieving tools: {e}")
    #     return []

# Example usage
tools = await get_playwright_tools()
if tools:
    # Use the tools
    pass

# %%
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import AgentExecutor#, create_react_agent # Changed import
# from langchain_community.chat_models import ChatOllama # Changed import
from langchain_ollama import ChatOllama
from langchain import hub
# from langchain.prompts import PromptTemplate  # Removed
from langchain.tools import Tool # Import Tool
from langgraph.prebuilt import create_react_agent

# %%
client = MultiServerMCPClient(
            {
                # "math": {
                #     "command": "python",
                #     # REPLACE WITH THE FULL ABSOLUTE PATH
                #     "args": ["math_server.py"],
                #     "transport": "stdio",
                # },
                "weather": {
                    # make sure you start your weather server on port 8000
                    "url": "http://localhost:8000/mcp",
                    # "transport": "streamable_http",
                }
            }
        )

# %%
from mcp.client.sse import sse_client
from mcp import ClientSession

# %%
SSE_URL =  "http://127.0.0.1:8000/mcp/"

# %%
headers = {"Authorization": f"Bearer auth_token","LOgesh_test": f"lusu ku"}
async with sse_client(url=SSE_URL,headers=headers) as (in_stream, out_stream):
    # 2) Create an MCP session over those streams
    async with ClientSession(in_stream, out_stream) as session:
        # 3) Initialize
        info = await session.initialize()
        # logger.info(f"Connected to {info.serverInfo.name} v{info.serverInfo.version}")

        # 4) List tools
        tools = (await session.list_tools())
        print(tools)

# %%
tools = await client.get_tools()
tools

# %%
model = ChatOllama(model="llama3.2:3b")

# %%
agent = create_react_agent(model=model, tools=tools,)  # Changed

# %%
response = await agent.ainvoke({"messages": "Get weather in New York"})

# %%
response

# %%
from fastmcp import Client

async with Client(
    "http://127.0.0.1:8000/mcp/", 
    auth="<your-token>",
) as client:
    x = await client.list_tools()
    print(x)

    x = await client.list_tools_mcp()
    print(x)

# %%
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.client.auth import BearerAuth

transport = StreamableHttpTransport(
    "http://127.0.0.1:8001/mcp/", 
    auth=BearerAuth(token="employee-token"),
    headers={"authorization1": "Bearer logesh"}
)

# %%
async with Client(transport) as client:
    ping = await client.ping()
    tools = await client.list_tools()
    # tools -> list[mcp.types.Tool]
    print(tools)
    # for tool in tools:
    #     # print(dir(tool))
    #     print(f"Tool: {tool.name}")
        # print(f"Description: {tool.description}")
    #     if tool.inputSchema:
    #         print(f"Parameters: {tool.inputSchema}")

    result = await client.call_tool("apply_leave", {"employee_id":"HI","reason":"hi"})
    # print(result)

    # result = await client.call_tool("get_user_info")
    print(result)

    # result = await client.call_tool("safe_header_info")
    # print(result)

# %%
from fastmcp import Client, Context, FastMCP

# %%
import requests

# API endpoint
url = "http://127.0.0.1:8000/"

# Bearer token
headers = {
    "Authorization": "Bearer secret-token-123",
    "testing":"HI, How are you ?"
}

# Make the GET request
response = requests.get(url, headers=headers)

# Print response
if response.status_code == 200:
    print("✅ Success:", response.json())
else:
    print("❌ Error:", response.status_code, response.text)

# %%
response.headers

# %%
# basic import 
from mcp.server.fastmcp import FastMCP
import math
import uvicorn
from starlette.applications import Starlette
# from routes import routes

# instantiate an MCP server client
mcp = FastMCP("Hello World")

# %%
starlette_app = mcp.streamable_http_app()

# %%
starlette_app.

# %%
uvicorn.run(starlette_app, host="0.0.0.0", port=8000)

# %%



