from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
import time

app = FastAPI()

bearer_scheme = HTTPBearer()

# Dummy tokens database
fake_tokens_db = {
    "secret-token-123": {"user_id": 1, "role": "admin"},
    "user-token-456": {"user_id": 2, "role": "user"},
}

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    user_data = fake_tokens_db.get(token)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token",
        )
    return user_data

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.get("/")
def secure_data(current_user: dict = Depends(get_current_user)):
    return {
        "message": "You have accessed secure data!",
        "user_id": current_user["user_id"],
        "role": current_user["role"]
    }

# 🟢 Run server directly from Python script
if __name__ == "__main__":
    # uvicorn.run(app, host="127.0.0.1", port=8000)
    uvicorn.run("fastapi_bearer:app", host="127.0.0.1", port=8000, reload=True)


# from fastapi import FastAPI, Depends, HTTPException, status
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# # from fastmcp.server import MCPServer
# from fastmcp import FastMCP
# from fastmcp import FastMCP, Context, tools
# from fastmcp.server.dependencies import get_access_token, AccessToken
# # from fastmcp.server.tool import tool
# # from fastmcp.server

# from fastmcp.server.middleware import Middleware, MiddlewareContext
# from fastmcp.server.middleware.middleware import ListToolsResult
# from fastmcp.exceptions import ToolError

# app = FastAPI()
# bearer_scheme = HTTPBearer()
# mcp = FastMCP("testing fastmcp")

# # Dummy Bearer auth
# fake_tokens_db = {
#     "secret-token-123": {"user_id": 1, "role": "admin"},
#     "user-token-456": {"user_id": 2, "role": "user"},
# }

# def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
#     token = credentials.credentials
#     user = fake_tokens_db.get(token)
#     if not user:
#         raise HTTPException(status_code=401, detail="Invalid token")
#     return user

# # Register a tool that requires auth
# # @mcp.tool(name="get_user_info", description="Get user info from token")
# # def get_user_info(user=Depends(get_current_user)):
# #     return {
# #         "message": "Accessed secure data",
# #         "user_id": user["user_id"],
# #         "role": user["role"]
# #     }

# # @mcp.tool
# # async def get_my_data(ctx: Context) -> dict:
# #     access_token: AccessToken = get_access_token()
    
# #     user_id = access_token.client_id  # From JWT 'sub' or 'client_id' claim
# #     user_scopes = access_token.scopes
    
# #     if "data:read_sensitive" not in user_scopes:
# #         raise ToolError("Insufficient permissions: 'data:read_sensitive' scope required.")
    
# #     return {
# #         "user": user_id,
# #         "sensitive_data": f"Private data for {user_id}",
# #         "granted_scopes": user_scopes
# #     }

# # Mount the MCP Server into FastAPI
# # app.mount("/mcp", mcp.streamable_http_app())
# # app = FastMCP.from_fastapi(
# #         app=mcp,
# #         name="fastmcp"
# #         # route_maps=[
# #         #     RouteMap(methods="*", pattern=r".*", mcp_type=MCPType.TOOL, tags={"admin"}),
# #         #     RouteMap(methods=["GET"], pattern=r".*", mcp_type=MCPType.RESOURCE),
# #         # ],
# #     )

# class ListingFilterMiddleware(Middleware):
#     async def on_list_tools(self, context: MiddlewareContext, call_next):
#         list_of_tools = await call_next(context)
        
#         # Filter out tools with "private" tag
#         # filtered_tools = {
#         #     name: tool for name, tool in list_of_tools
#         #     if "private" not in tool.tags
#         # }
        
#         filtered_tools = [tool for tool in list_of_tools if "employee" in tool.tags]

#         # Return modified result
#         return filtered_tools
#         return ListToolsResult(tools=filtered_tools)
    
#     async def on_call_tool(self, context: MiddlewareContext, call_next):
#         # Access the tool object to check its metadata
#         if context.fastmcp_context:
#             try:
#                 tool = await context.fastmcp_context.fastmcp.get_tool(context.message.name)
                
#                 # Check if this tool has a "private" tag
#                 if "employee" in tool.tags:
#                     raise ToolError("Access denied: private tool")
                    
#                 # Check if tool is enabled
#                 if not tool.enabled:
#                     raise ToolError("Tool is currently disabled")
                    
#             except Exception:
#                 # Tool not found or other error - let execution continue
#                 # and handle the error naturally
#                 pass
        
#         return await call_next(context)
    
# mcp_app = mcp.streamable_http_app(path='/mcp')
# mcp_app.add_middleware(ListingFilterMiddleware())
# # mcp = FastAPI(lifespan=mcp_app.lifespan)
# # app.mount("", mcp_app)


# # mcp = FastMCP.from_fastapi(app=app)

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("fastapi_bearer:app", host="127.0.0.1", port=8000, reload=True)
