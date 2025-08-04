from fastmcp import FastMCP, Context
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastmcp.server.dependencies import get_context
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.dependencies import get_http_headers
from fastmcp.exceptions import ToolError
import time
from langfuse import observe
from langfuse import Langfuse
from fastmcp.tools import Tool
from fastmcp.tools.tool_transform import forward, ArgTransform
from functools import wraps


langfuse = Langfuse(
  secret_key="sk-lf-8581db31-f2ca-4f3d-82b8-ab5f873132da",
  public_key="pk-lf-ca4bf373-d6d1-4c99-9133-cedbe6ff9d5d",
  host="https://us.cloud.langfuse.com"
)

# Create a basic server instance
first_mcp = FastMCP(name="MyAssistantServer",mask_error_details=True)

class UserAuthMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):

        # Middleware stores user info in context state
        context.fastmcp_context.set_state("user_id", "user_123")
        context.fastmcp_context.set_state("permissions", ["read", "write"])
        
        return await call_next()
    
@first_mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request):
    return JSONResponse({"status": "healthy"})

@first_mcp.tool()
async def add(a: int, b:int=0) -> int:
    """Adds two integer numbers together."""
    return a

async def process_data(data) -> dict:
    # Get the active context - only works when called within a request
    ctx = get_context()    
    await ctx.info(f"Processing {len(data)} data points")

@first_mcp.tool(exclude_args=["user_id"])
async def testing(user_id = ""):
    print(" User id",user_id)
    # a = await process_data(user_id)
    return user_id


@first_mcp.tool()
async def my_tool(ctx: Context) -> str:
    result = await ctx.elicit("Choose an action")

    if result.action == "accept":
        return "Accepted!"
    elif result.action == "decline":
        return "Declined!"
    else:
        return "Cancelled!"


from fastmcp import FastMCP

class ComponentProvider:
    def __init__(self, mcp_instance):
        # Register methods
        mcp_instance.tool(self.tool_method)
        mcp_instance.resource("resource://data")(self.resource_method)
    
    def dec(func):

        @wraps(func)
        @observe(name=func.__name__)
        def inner(*args, **kwargs):
            print('decorated function')
            print(args)
            print(kwargs)
            return func(*args, **kwargs)
        return inner
    
    @dec
    def tool_method(self, x, langfuse_trace_id=None):
        return x * 2
    
    def resource_method(self):
        return "Resource data"
    
# The methods are automatically registered when creating the instance
provider = ComponentProvider(first_mcp)

# async def ensure_a_positive(a: int, **kwargs) -> int:
#     if a <= 0:
#         raise ValueError("a must be positive")
#     return await forward(a=a, **kwargs)

# new_tool = Tool.from_tool(
#     add,
#     transform_fn=ensure_a_positive,
#     transform_args={
#         "x": ArgTransform(name="a"),
#         "y": ArgTransform(name="b"),
#     }
# )

# first_mcp.add_tool(new_tool)



class ListingFilterMiddleware(Middleware):

    # @observe()
    async def on_list_tools(self, context: MiddlewareContext, call_next):
        result = await call_next(context)
        
        # Filter out tools with "private" tag
        filtered_tools = [
            tool for tool in result 
            if "private" not in tool.tags
        ]
        
        # Return modified list
        return filtered_tools

    # @observe()
    async def on_request(self, context: MiddlewareContext, call_next):
        start_time = time.perf_counter()
        
        try:
            result = await call_next(context)
            duration_ms = (time.perf_counter() - start_time) * 1000
            print(f"Request {context.method} completed in {duration_ms:.2f}ms")
            return result
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            print(f"Request {context.method} failed after {duration_ms:.2f}ms: {e}")
            raise

    # @observe()
    async def on_message(self, context: MiddlewareContext, call_next):
        """Called for all MCP messages."""
        print(f"Processing {context.method} from {context.source}")
        
        result = await call_next(context)
        
        print(f"Completed {context.method}")
        return result

    # @observe()
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        # Access the tool object to check its metadata
        if context.fastmcp_context:
            try:
                tool = await context.fastmcp_context.fastmcp.get_tool(context.message.name)
                
                # permissions = context.get_state("permissions")
                removed = [context.message.arguments.pop(x) for x in (context.message.arguments.keys() - tool.parameters['properties'].keys())]
                # Check if this tool has a "private" tag
                if "private" in tool.tags:
                    raise ToolError("Access denied: private tool")
                    
                # Check if tool is enabled
                if not tool.enabled:
                    raise ToolError("Tool is currently disabled")
                    
            except Exception as e:
                # Tool not found or other error - let execution continue
                # and handle the error naturally
                print(e)
                pass

        # @observe()
        x = await call_next(context)
        return x


first_mcp.add_middleware(ListingFilterMiddleware())
# Create ASGI app with middleware
first_mcp_app = first_mcp.http_app(path="/mcp",stateless_http=True, transport="streamable-http")








