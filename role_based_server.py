# import anyio
# import warnings
# from functools import partial
# from typing import Any, Awaitable, Callable, Literal

# from starlette.middleware import Middleware as ASGIMiddleware
# from starlette.requests import Request
# from starlette.responses import JSONResponse, Response

# import fastmcp
# from fastmcp import FastMCP
# from fastmcp.exceptions import NotFoundError
# from fastmcp.server.middleware import Middleware, MiddlewareContext
# from fastmcp.tools import Tool

# from starlette.middleware.base import BaseHTTPMiddleware
# from starlette.requests import Request
# from starlette.responses import JSONResponse

# # --- Mock User Database and Roles ---
# # In a real application, this would be a proper database lookup.
# ROLES = ["employee", "manager", "md"]
# USER_TOKENS = {
#     "token_employee_alice": {"name": "Alice", "role": "employee"},
#     "token_manager_bob": {"name": "Bob", "role": "manager"},
#     "token_md_carol": {"name": "Carol", "role": "md"},
# }

# # Role hierarchy: higher roles inherit permissions of lower roles.
# ROLE_HIERARCHY = {
#     "md": ["md", "manager", "employee"],
#     "manager": ["manager", "employee"],
#     "employee": ["employee"],
# }


# # --- Server Definition ---
# # Suppress deprecation warnings for this example for cleaner output
# fastmcp.settings.deprecation_warnings = False

# # We will add middleware later
# server = FastMCP(
#     name="CorporateToolServer",
#     instructions="A server with tools for corporate employees, with role-based access control.",
# )


# # --- Tool Definitions ---
# # We use tags to define the minimum role required to access a tool.

# @server.tool(tags={"role:employee"})
# def submit_expense_report(amount: float, description: str) -> str:
#     """Submits an expense report for the current user."""
#     # In a real app, you'd get the user from the context
#     return f"Expense report for {amount:.2f} ('{description}') submitted successfully."

# @server.tool(tags={"role:manager"})
# def approve_expense_report(report_id: int, approver_notes: str) -> dict:
#     """Approves an expense report submitted by a direct report."""
#     return {
#         "status": "approved",
#         "report_id": report_id,
#         "approved_by": "Current Manager", # From context
#         "notes": approver_notes,
#     }

# @server.tool(tags={"role:md"})
# def get_company_financials() -> dict:
#     """[CONFIDENTIAL] Retrieves the company's quarterly financial summary."""
#     return {
#         "revenue": "10.5M USD",
#         "profit": "2.1M USD",
#         "quarter": "Q4 2024",
#     }


# def get_required_role_from_tool(tool: Tool) -> str | None:
#     """Helper to extract 'role:...' tag from a tool."""
#     for tag in tool.tags:
#         if tag.startswith("role:"):
#             return tag.split(":", 1)[1]
#     return None

# async def role_based_auth_middleware(
#     context: MiddlewareContext[Any],
#     call_next: Callable[[MiddlewareContext[Any]], Awaitable[Any]],
# ) -> Any:
#     """
#     This FastMCP middleware handles AUTHORIZATION based on user role.
#     It assumes AUTHENTICATION has already happened and the user's role
#     is available in `context.fastmcp_context.state`.
#     """
#     print(f"\n--- Middleware running for method: {context.method} ---")

#     try:
#         # 1. Get the user's role, which we expect an earlier middleware to have set.
#         user_role = context.fastmcp_context.state.get("user_role")
#         if not user_role:
#             print("Middleware: No user role found in context. Denying access.")
#             raise NotFoundError("Authentication required.")
        
#         user_permissions = ROLE_HIERARCHY.get(user_role, [])
#         print(f"Middleware: User role is '{user_role}'. Permissions: {user_permissions}")

#         # 2. Authorize based on the MCP method being called.
#         if context.method == "tools/list":
#             # Let the default handler get the full list first.
#             response = await call_next(context)
            
#             # Now, filter the response based on the user's role.
#             all_tools: list[Tool] = response
#             accessible_tools = []
#             for tool in all_tools:
#                 required_role = get_required_role_from_tool(tool)
#                 if not required_role or required_role in user_permissions:
#                     accessible_tools.append(tool)
            
#             print(f"Middleware: Filtering tool list. {len(all_tools)} -> {len(accessible_tools)} accessible.")
#             return accessible_tools

#         elif context.method == "tools/call":
#             tool_name = context.message.name
#             print(f"Middleware: Authorizing call to tool '{tool_name}'.")
            
#             # Get the tool being called to check its required role.
#             try:
#                 tool = await server.get_tool(tool_name)
#             except NotFoundError:
#                 # If the tool doesn't exist, let the normal flow handle it.
#                 return await call_next(context)
                
#             required_role = get_required_role_from_tool(tool)
            
#             if required_role and required_role not in user_permissions:
#                 print(f"Middleware: DENIED. User role '{user_role}' cannot access tool '{tool_name}' (requires '{required_role}').")
#                 # Raise NotFoundError to hide the existence of the tool from unauthorized users.
#                 raise NotFoundError(f"Unknown tool: {tool_name}")
            
#             print(f"Middleware: ALLOWED. User can access '{tool_name}'.")
#             # If authorized, proceed to the actual tool call.
#             return await call_next(context)

#         else:
#             # For any other method (e.g., resources/list), let it pass through.
#             print(f"Middleware: Method '{context.method}' does not require role check. Allowing.")
#             return await call_next(context)

#     except Exception as e:
#         print(f"Middleware: An error occurred: {e}")
#         raise # Re-raise the exception to be handled by the server.

# # Now add our custom middleware to the server instance.
# server.add_middleware(role_based_auth_middleware)

# async def bearer_token_auth_asgi_middleware(request: Request, call_next: Callable):
#     """
#     This is an ASGI middleware. It runs before FastMCP.
#     It's responsible for AUTHENTICATION. It checks the HTTP Authorization header,
#     finds the user, and puts their info into the FastMCP context state for
#     later use by our authorization middleware.
#     """
#     auth_header = request.headers.get("Authorization")
#     if not auth_header or not auth_header.startswith("Bearer "):
#         return JSONResponse(
#             status_code=401,
#             content={"error": "Unauthorized", "detail": "Bearer token missing or invalid."},
#         )

#     token = auth_header.split(" ", 1)[1]
#     user_info = USER_TOKENS.get(token)

#     if not user_info:
#         return JSONResponse(
#             status_code=403,
#             content={"error": "Forbidden", "detail": "Invalid token."},
#         )
    
#     # This is the key part: we inject user data into the context's state.
#     # The FastMCP server will create a context per request, and this state
#     # will be available to all FastMCP middleware and handlers.
#     fastmcp.server.context.get_context().state["user_role"] = user_info["role"]
#     fastmcp.server.context.get_context().state["user_name"] = user_info["name"]

#     response = await call_next(request)
#     return response


# print(f"Server '{server.name}' created with {len(server._tool_manager._tools)} tools.")

# async def main():
#     # We create the ASGI middleware instance. `dispatch=` is the argument name.
#     asgi_middlewares = [ASGIMiddleware(bearer_token_auth_asgi_middleware)]
    
#     print("\nStarting server on http://127.0.0.1:8000/mcp")
#     print("Use an Authorization: Bearer <token> header to authenticate.")
#     print(f"Available tokens: {list(USER_TOKENS.keys())}")
    
#     await server.run_http_async(
#         host="127.0.0.1",
#         port=8000,
#         path="/mcp",
#         middleware=asgi_middlewares,
#     )

# if __name__ == "__main__":
#     anyio.run(main)


# from fastmcp.server.server import FastMCP 
# from fastmcp.tools.tool import Tool 
# from fastmcp.server.auth.auth import OAuthProvider 
# from fastmcp.server.middleware import MiddlewareContext 
# from starlette.requests import Request 
# from starlette.responses import JSONResponse 
# from starlette.exceptions import HTTPException 
# import asyncio


# def apply_leave(employee_id: str, reason: str) -> str: return f"Leave applied for {employee_id} due to {reason}"

# def approve_leave(request_id: str) -> str: return f"Leave request {request_id} approved"


# class RoleBasedBearerAuth(OAuthProvider): 
#     def __init__(self,url):
#         super().__init__(url)

#     async def authenticate(self, request: Request) -> dict: 
#         token = request.headers.get("Authorization", "").replace("Bearer ", "")

#     # Example: token to role mapping (can be DB or env based)
#         if token == "employee-token":
#             return {"user": "employee_1", "role": "employee", "url": str(request.url)}
#         elif token == "manager-token":
#             return {"user": "manager_1", "role": "manager", "url": str(request.url)}
#         else:
#             raise HTTPException(status_code=401, detail="Unauthorized")

# async def role_filter_middleware(context: MiddlewareContext, call_next): 
#     role = context.request_context.get("role") or context.request_context.get("user", {}).get("role")

#     if context.method == "tools/list":
#         tools = await call_next(context)
#         return [tool for tool in tools if "roles" not in tool.tags or role in tool.tags["roles"]]

#     return await call_next(context)


# apply_leave_tool = Tool.from_function( apply_leave, name="apply_leave", tags={"roles": ["employee", "manager"]}, ) 
# approve_leave_tool = Tool.from_function( approve_leave, name="approve_leave", tags={"roles": ["manager"]}, )

# server = FastMCP( 
#     name="LeaveManagementMCP",
#     instructions="Use tools to apply or approve leaves.",
#     auth=RoleBasedBearerAuth("http://127.0.0.1:6274/mcp"),
#     middleware=[role_filter_middleware], 
#     tools=[apply_leave_tool, approve_leave_tool], 
#     )


# @server.custom_route("/health", methods=["GET"]) 
# async def health_check(request: Request): 
#     return JSONResponse({"status": "ok"})


# if __name__ == "__main__": 
#     server.run( transport="streamable-http", host="0.0.0.0", port=8000, )


"""
Example demonstrating RouteMap tags functionality.

This example shows how to use the tags parameter in RouteMap
to selectively route OpenAPI endpoints based on their tags.
"""

import asyncio

from fastapi import FastAPI

from fastmcp import FastMCP
from fastmcp.server.openapi import MCPType, RouteMap

# Create a FastAPI app with tagged endpoints
app = FastAPI(title="Tagged API Example")


@app.get("/users", tags=["users", "public"])
async def get_users():
    """Get all users - public endpoint"""
    return [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]


@app.post("/users", tags=["users", "admin"])
async def create_user(name: str):
    """Create a user - admin only"""
    return {"id": 3, "name": name}


@app.get("/admin/stats", tags=["admin", "internal"])
async def get_admin_stats():
    """Get admin statistics - internal use"""
    return {"total_users": 100, "active_sessions": 25}


@app.get("/health", tags=["public"])
async def health_check():
    """Public health check"""
    return {"status": "healthy"}


@app.get("/metrics")
async def get_metrics():
    """Metrics endpoint with no tags"""
    return {"requests": 1000, "errors": 5}


async def main():
    """Demonstrate different tag-based routing strategies."""

    print("=== Example 1: Make admin-tagged routes tools ===")

    # Strategy 1: Convert admin-tagged routes to tools
    mcp1 = FastMCP.from_fastapi(
        app=app,
        route_maps=[
            RouteMap(methods="*", pattern=r".*", mcp_type=MCPType.TOOL, tags={"admin"}),
            RouteMap(methods=["GET"], pattern=r".*", mcp_type=MCPType.RESOURCE),
        ],
    )

    tools = await mcp1.get_tools()
    resources = await mcp1.get_resources()

    print(f"Tools ({len(tools)}): {', '.join(tools.keys())}")
    print(f"Resources ({len(resources)}): {', '.join(resources.keys())}")

    print("\n=== Example 2: Exclude internal routes ===")

    # Strategy 2: Exclude internal routes entirely
    mcp2 = FastMCP.from_fastapi(
        app=app,
        route_maps=[
            RouteMap(
                methods="*", pattern=r".*", mcp_type=MCPType.EXCLUDE, tags={"internal"}
            ),
            RouteMap(methods=["GET"], pattern=r".*", mcp_type=MCPType.RESOURCE),
            RouteMap(methods=["POST"], pattern=r".*", mcp_type=MCPType.TOOL),
        ],
    )

    tools = await mcp2.get_tools()
    resources = await mcp2.get_resources()

    print(f"Tools ({len(tools)}): {', '.join(tools.keys())}")
    print(f"Resources ({len(resources)}): {', '.join(resources.keys())}")

    print("\n=== Example 3: Pattern + Tags combination ===")

    # Strategy 3: Routes matching both pattern AND tags
    mcp3 = FastMCP.from_fastapi(
        app=app,
        route_maps=[
            # Admin routes under /admin path -> tools
            RouteMap(
                methods="*",
                pattern=r".*/admin/.*",
                mcp_type=MCPType.TOOL,
                tags={"admin"},
            ),
            # Public routes -> tools
            RouteMap(
                methods="*", pattern=r".*", mcp_type=MCPType.TOOL, tags={"public"}
            ),
            RouteMap(methods=["GET"], pattern=r".*", mcp_type=MCPType.RESOURCE),
        ],
    )

    tools = await mcp3.get_tools()
    resources = await mcp3.get_resources()

    print(f"Tools ({len(tools)}): {', '.join(tools.keys())}")
    print(f"Resources ({len(resources)}): {', '.join(resources.keys())}")

    print("\n=== Example 4: Multiple tag AND condition ===")

    # Strategy 4: Routes must have ALL specified tags
    mcp4 = FastMCP.from_fastapi(
        app=app,
        route_maps=[
            # Routes with BOTH "users" AND "admin" tags -> tools
            RouteMap(
                methods="*",
                pattern=r".*",
                mcp_type=MCPType.TOOL,
                tags={"users", "admin"},
            ),
            RouteMap(methods=["GET"], pattern=r".*", mcp_type=MCPType.RESOURCE),
        ],
    )

    tools = await mcp4.get_tools()
    resources = await mcp4.get_resources()

    print(f"Tools ({len(tools)}): {', '.join(tools.keys())}")
    print(f"Resources ({len(resources)}): {', '.join(resources.keys())}")


if __name__ == "__main__":
    asyncio.run(main())
