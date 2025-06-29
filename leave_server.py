from typing import Any, Awaitable, Callable

# FastMCP and Starlette imports
import fastmcp
from fastmcp import FastMCP
from fastmcp.exceptions import NotFoundError
from fastmcp.server.auth.auth import OAuthProvider
from fastmcp.server.middleware import MiddlewareContext
from fastmcp.tools import Tool
from starlette.middleware import Middleware as ASGIMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException
import anyio, time
# --- 1. Role-based Bearer Auth Provider ---
# Handles AUTHENTICATION by checking the token and returning user context.
class RoleBasedBearerAuth(OAuthProvider):
    async def authenticate(self, request: Request) -> dict:
        """
        Authenticates the request based on the Authorization header.
        Returns a dictionary with user info, which becomes available in the context.
        """
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        print(f"[AUTH] Authenticating with token: '{token}'")
        
        # In a real app, this would be a database/API call.
        if token == "employee-token":
            return {"user": "employee_1", "role": "employee"}
        elif token == "manager-token":
            return {"user": "manager_1", "role": "manager"}
        else:
            # If the token is invalid, we deny access at the HTTP level.
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing token")


# --- 2. Middleware for Authorization ---
# Handles AUTHORIZATION by checking the user's role against the tool's requirements.
async def role_based_auth_middleware(
    context: MiddlewareContext[Any],
    # request: Request,
    call_next: Callable[[MiddlewareContext[Any]], Awaitable[Any]],
) -> Any:
    """
    A complete authorization middleware. It checks both 'tools/list' and 'tools/call'.
    It runs after the OAuthProvider and uses the context it provides.
    """
    # Get the authentication context provided by our RoleBasedBearerAuth provider.
    # auth_context = context.fastmcp_context.auth
    # if not auth_context:
    #     raise NotFoundError("Authentication context is missing. This should not happen if auth is configured.")
        
    user_role = auth_context.get("role")
    if not user_role:
        raise NotFoundError("User role not found in authentication context.")

    print(f"[MIDDLEWARE] User role: '{user_role}' | Method: '{context.method}'")

    # A. Handle filtering the list of tools
    if context.method == "tools/list":
        # Let the default handler get the full list of tools first.
        all_tools: list[Tool] = await call_next(context)
        
        # Now, filter the list based on the user's role.
        accessible_tools = []
        for tool in all_tools:
            # A tool's required roles are stored in its tags, e.g., "role:manager"
            required_roles = {tag.split(":", 1)[1] for tag in tool.tags if tag.startswith("role:")}
            # If the tool has no role requirements, or the user's role is in the list, it's accessible.
            if not required_roles or user_role in required_roles:
                accessible_tools.append(tool)
        
        print(f"[MIDDLEWARE] Filtering tools: {len(all_tools)} total -> {len(accessible_tools)} accessible for '{user_role}'.")
        return accessible_tools

    # B. Handle authorizing a direct tool call (CRITICAL SECURITY STEP)
    if context.method == "tools/call":
        tool_name = context.message.name
        try:
            tool_to_call = await server.get_tool(tool_name)
        except NotFoundError:
            # If the tool doesn't exist anyway, let the default handler manage it.
            return await call_next(context)
            
        required_roles = {tag.split(":", 1)[1] for tag in tool_to_call.tags if tag.startswith("role:")}
        if required_roles and user_role not in required_roles:
            print(f"[MIDDLEWARE] DENIED call to '{tool_name}' for role '{user_role}'. Requires one of: {required_roles}")
            # Raise NotFoundError to hide the existence of the tool from unauthorized users.
            raise NotFoundError(f"Unknown tool: {tool_name}")
        
        print(f"[MIDDLEWARE] ALLOWED call to '{tool_name}' for role '{user_role}'.")

    # For all other methods (e.g., resources/list), let them pass through.
    return await call_next(context)

async def bearer_token_auth_asgi_middleware(request, call_next):
    """
    This is an ASGI middleware. It runs before FastMCP.
    It's responsible for AUTHENTICATION. It checks the HTTP Authorization header,
    finds the user, and puts their info into the FastMCP context state for
    later use by our authorization middleware.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized", "detail": "Bearer token missing or invalid."},
        )

    token = auth_header.split(" ", 1)[1]
    user_info = USER_TOKENS.get(token)

    if not user_info:
        return JSONResponse(
            status_code=403,
            content={"error": "Forbidden", "detail": "Invalid token."},
        )
    
    # This is the key part: we inject user data into the context's state.
    # The FastMCP server will create a context per request, and this state
    # will be available to all FastMCP middleware and handlers.
    fastmcp.server.context.get_context().state["user_role"] = user_info["role"]
    fastmcp.server.context.get_context().state["user_name"] = user_info["name"]

    response = await call_next(request)
    return response

USER_TOKENS = {
    "token_employee_alice": {"name": "Alice", "role": "employee"},
    "token_manager_bob": {"name": "Bob", "role": "manager"},
    "token_md_carol": {"name": "Carol", "role": "md"},
}

from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.middleware.middleware import ListToolsResult
from fastmcp.exceptions import ToolError

class ListingFilterMiddleware(Middleware):
    async def on_list_tools(self, context: MiddlewareContext, call_next):
        list_of_tools = await call_next(context)
        
        # Filter out tools with "private" tag
        # filtered_tools = {
        #     name: tool for name, tool in list_of_tools
        #     if "private" not in tool.tags
        # }
        
        filtered_tools = [tool for tool in list_of_tools if "employee" in tool.tags]

        # Return modified result
        return filtered_tools
        return ListToolsResult(tools=filtered_tools)
    
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        # Access the tool object to check its metadata
        if context.fastmcp_context:
            try:
                tool = await context.fastmcp_context.fastmcp.get_tool(context.message.name)
                
                # Check if this tool has a "private" tag
                if "employee1" in tool.tags:
                    raise ToolError("Access denied: private tool")
                    
                # Check if tool is enabled
                if not tool.enabled:
                    raise ToolError("Tool is currently disabled")
                
                x = await call_next(context)
                return x
            
            except Exception as e:
                # Tool not found or other error - let execution continue
                # and handle the error naturally
                return "Access denied: private tool"
    
# --- 3. Create FastMCP Server ---
# We instantiate the server with our custom auth provider and middleware.

async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    # response.headers["X-Process-Time"] = str(process_time)
    return response

asgi_middlewares = [ASGIMiddleware(bearer_token_auth_asgi_middleware)]
server = FastMCP(
    name="LeaveManagementMCP",
    instructions="Use tools to apply for or approve leaves.",
    # auth=RoleBasedBearerAuth(),
    # middleware=bearer_token_auth_asgi_middleware,
)
server.add_middleware(bearer_token_auth_asgi_middleware)
server.add_middleware(add_process_time_header)
server.add_middleware(ListingFilterMiddleware())

# --- 4. Define Tools with Decorators ---
# This is the modern, ergonomic way to define and register tools.
# We use the `tags` parameter to specify role requirements.

@server.tool(tags={"employee", "manager"})
def apply_leave(employee_id: str, reason: str):
    """Applies for a leave of absence."""
    return f"Leave applied for {employee_id} due to {reason}"

@server.tool(tags={"manager"})
def approve_leave(request_id: str):
    """Approves a leave request. Only available to managers."""
    return f"Leave request {request_id} approved"

# --- 5. Define Custom HTTP Routes ---
# Useful for things like health checks that are outside the MCP protocol.
@server.custom_route("/health", methods=["GET"])
async def health_check(request: Request):
    """A simple health check endpoint."""
    return JSONResponse({"status": "ok"})

# --- 6. Run the Server ---
# The entry point for our application.
async def main():
    print("--- Starting Leave Management MCP Server ---")
    print("Server running on: http://127.0.0.1:8000/mcp")
    print("Health check on: http://127.0.0.1:8000/health")
    print("\n--- Test Tokens ---")
    print("Employee : Authorization: Bearer employee-token")
    print("Manager  : Authorization: Bearer manager-token")
    print("-------------------------------------------\n")
    
    # Use the synchronous server.run() method.
    # It handles the async event loop internally.
    await server.run_http_async(
        # transport="http",
        host="127.0.0.1",
        port=8001,
        # middleware=asgi_middlewares,
        path="/mcp" # The main path for MCP communication
    )

if __name__ == "__main__":
    anyio.run(main)
