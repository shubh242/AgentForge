from fastapi import FastAPI
from .mcp_server import router as mcp_router

app = FastAPI(title="AgentForge MCP Server", version="0.1.0")
app.include_router(mcp_router, prefix="/mcp")

@app.get("/")
async def health():
    return {"status": "ok"}
