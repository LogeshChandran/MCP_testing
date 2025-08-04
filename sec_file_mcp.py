from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

# Create a basic server instance
sec_mcp = FastMCP(name="MyAssistantServer 2")

@sec_mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request):
    return JSONResponse({"status": "healthy"})

@sec_mcp.tool()
def mul(a: int, b: int) -> int:
    """Adds two integer numbers together."""
    return a + b

# Create ASGI app with middleware
sec_mcp_app = sec_mcp.http_app(path="/mcp",stateless_http=True, transport="streamable-http")


