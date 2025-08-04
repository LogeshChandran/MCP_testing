from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.applications import Starlette
from starlette.routing import Mount
from contextlib import asynccontextmanager
from first_mcp import first_mcp_app
from sec_mcp import sec_mcp_app
import uvicorn

# Define custom middleware
custom_middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

@asynccontextmanager
async def app_lifespan(app):
    async with first_mcp_app.lifespan(app):
        async with sec_mcp_app.lifespan(app):
            yield

# Create a Starlette app and mount the MCP server
app = Starlette(
    debug=True,
    routes=[
        Mount("/first_mcp", app=first_mcp_app),
        Mount("/sec_mcp", app=sec_mcp_app),
    ],
    middleware=custom_middleware,
    lifespan=app_lifespan
)

if __name__ == "__main__":
    uvicorn.run("server:app", host='0.0.0.0', port=8010, reload=True)
