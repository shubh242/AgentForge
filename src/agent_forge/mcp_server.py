from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from .tools.postgres_tool import PostgresQueryTool
from .tools.github_tool import GithubTool
from .tools.rag_tool import RAGTool

router = APIRouter()


class ToolMetadata(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]


class ToolCall(BaseModel):
    tool: str
    args: dict[str, Any]


@router.get("/tools")
async def list_tools() -> list[ToolMetadata]:
    return [
        ToolMetadata(
            name="postgres_query",
            description="Run a read-only SQL query against Postgres.",
            input_schema={"query": "string"},
        ),
        ToolMetadata(
            name="list_open_prs",
            description="Fetches all the open PRs from a specific Github repository.",
            input_schema={"owner_name": "string", "repo_name": "string"},
        ),
        ToolMetadata(
            name="get_file_contents",
            description="Retrieves the file content of the requested path in the Github repository",
            input_schema={"owner_name": "string", "repo_name": "string", "file_path": "string"},
        ),
        ToolMetadata(
            name="rag_search",
            description="Search the local documentation vector database for context",
            input_schema={"query": "string"},
        )
    ]


@router.post("/call")
async def call_tool(request: ToolCall) -> Any:
    if request.tool == "postgres_query":
        try:
            return await PostgresQueryTool().run(request.args)
        except ValidationError as e:
            raise HTTPException(
                status_code=422,
                detail=f"Query validation failed: {e.errors()[0]['msg']}",
            )
    elif request.tool == "list_open_prs":
        try:
            return await GithubTool().list_open_prs(request.args)
        except ValidationError as e:
            raise HTTPException(
                status_code=422,
                detail=f"Query validation failed: {e.errors()[0]['msg']}",
            )
    elif request.tool == "get_file_contents":
        try:
            return await GithubTool().get_file_contents(request.args)
        except ValidationError as e:
            raise HTTPException(
                status_code=422,
                detail=f"Query validation failed: {e.errors()[0]['msg']}",
            )
    elif request.tool == "rag_search":
        try:
            return await RAGTool().rag_search(request.args)
        except ValidationError as e:
            raise HTTPException(
                status_code=422,
                detail=f"Query validation failed: {e.errors()[0]['msg']}",
            )

    raise HTTPException(status_code=404, detail=f"Unknown tool: {request.tool}")
