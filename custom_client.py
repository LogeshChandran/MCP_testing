from typing import TypedDict, List, Any
from typing import Annotated
import operator

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import chain
from langchain_core.tools import BaseTool
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables import chain
from langgraph.graph import MessageGraph, StateGraph, END
from chatollama import ChatOllama
from langchain_core.utils.function_calling import convert_to_openai_function
from langchain_core.tools import Tool
import requests

class AgentState(TypedDict):
    messages: Annotated[list[Any], operator.add]

from langgraph.checkpoint.sqlite import SqliteSaver
memory = SqliteSaver.from_conn_string(":memory:")

class Agent:
    def __init__(self, model, tools, checkpointer, system=""):
        self.system = system
        graph = StateGraph(AgentState)
        graph.add_node("llm", self.call_llm)  # Renamed to call_llm
        graph.add_node("action", self.take_action)
        graph.add_conditional_edges("llm", self.exists_action, {True: "action", False: END})
        graph.add_edge("action", "llm")
        graph.set_entry_point("llm")
        self.graph = graph.compile(checkpointer=checkpointer)
        self.tools = {t.name: t for t in tools}
        self.model = model  # Removed .bind_tools(tools) - ChatOllama handles tools differently

    def call_llm(self, state: AgentState):  # Renamed to call_llm
        messages = state['messages']
        if self.system:
            messages = [SystemMessage(content=self.system)] + messages
        message = self.model.invoke({"messages": messages, "tools": [tool.to_pydantic() for tool in self.tools.values()]}) # Modified to ChatOllama format

        return {'messages': [message]}

    def exists_action(self, state: AgentState):
        result = state['messages'][-1]
        if hasattr(result, 'tool_calls') and result.tool_calls:
            return True
        else:
            return False

    def take_action(self, state: AgentState):
        tool_calls = state['messages'][-1].tool_calls
        results = []
        for t in tool_calls:
            print(f"Calling: {t}")
            result = self.tools[t.name].invoke(t.args)
            results.append(ToolMessage(tool_call_id=t.id, content=str(result)))
        print("Back to the model!")
        return {'messages': results}

def get_tools_from_mcp(url="http://localhost:3000/mcp"):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        tools_data = response.json()

        tools = []
        for tool_data in tools_data:
            # Assuming each tool_data has 'name', 'description', and 'func' keys
            name = tool_data['name']
            description = tool_data['description']

            # Create a Tool instance.  We need a callable 'func'.  For now, we'll use a lambda that just returns a string indicating the tool was called.  You'll need to replace this with actual tool implementations.
            func = lambda input_str: f"Tool '{name}' called with input: {input_str}"  # Replace with actual tool logic

            tool = Tool(name=name, description=description, func=func)
            tools.append(tool)

        return tools

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to MCP server: {e}")
        return []  # Or raise the exception, depending on how you want to handle errors

# Example usage:
tools = get_tools_from_mcp()

prompt = """You are a smart research assistant. Use the tools to look up information. \
You are allowed to make multiple calls (either together or in sequence). \
Only look up information when you are sure of what you want. \
If you need to look up some information before asking a follow up question, you are allowed to do that!
"""
model = ChatOllama(model="llama3.2")  # Changed to ChatOllama
abot = Agent(model, tools, system=prompt, checkpointer=memory)
messages = [HumanMessage(content="What is the weather in sf?")]
thread = {"configurable": {"thread_id": "1"}}
