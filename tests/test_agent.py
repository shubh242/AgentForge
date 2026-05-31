import pytest
from agent_forge.agent import Agent, ToolCall


@pytest.mark.anyio
async def test_agent_plan_ping():
    agent = Agent()
    # Task doesn't match any specific patterns, should fallback to ping after RAG
    result = await agent.run("Verify connection")
    assert len(result["steps_executed"]) == 2
    assert result["steps_executed"][0]["tool"] == "rag_search"
    assert result["steps_executed"][1]["tool"] == "postgres_query"
    assert result["steps_executed"][1]["args"]["query"] == "SELECT 1 AS ping"
    assert "No open Pull Requests" in result["summary"]


@pytest.mark.anyio
async def test_agent_plan_database_query():
    agent = Agent()
    # Task asks about schema
    result = await agent.run("Show me the users table schema")
    assert len(result["steps_executed"]) == 2
    assert result["steps_executed"][0]["tool"] == "rag_search"
    assert result["steps_executed"][1]["tool"] == "postgres_query"
    assert "users" in result["steps_executed"][1]["args"]["query"]


@pytest.mark.anyio
async def test_agent_plan_github_file_contents():
    agent = Agent()
    # Task asks for file contents
    result = await agent.run("Show me the file contents of README.md")
    assert len(result["steps_executed"]) == 2
    assert result["steps_executed"][0]["tool"] == "rag_search"
    assert result["steps_executed"][1]["tool"] == "get_file_contents"
    assert result["steps_executed"][1]["args"]["owner_name"] == "shubh242"
    assert result["steps_executed"][1]["args"]["repo_name"] == "clinicops-copilot"
    assert result["steps_executed"][1]["args"]["file_path"] == "README.md"


@pytest.mark.anyio
async def test_agent_loop_open_prs_touching_users_table():
    agent = Agent()
    # Task asks for open PRs touching the users table
    result = await agent.run("Summarize open PRs touching the users table")
    
    # It should have executed 3 steps:
    # 1. RAG search
    # 2. postgres_query to list open PRs
    # 3. list_open_prs on the repo containing 'users' (shubh242/clinicops-copilot)
    assert len(result["steps_executed"]) == 3
    
    step0 = result["steps_executed"][0]
    assert step0["tool"] == "rag_search"

    step1 = result["steps_executed"][1]
    assert step1["tool"] == "postgres_query"
    assert "status = 'open'" in step1["args"]["query"]
    
    step2 = result["steps_executed"][2]
    assert step2["tool"] == "list_open_prs"
    assert step2["args"]["owner_name"] == "shubh242"
    assert step2["args"]["repo_name"] == "clinicops-copilot"
    
    # Verify synthesized response has the PR details
    assert "open Pull Request(s)" in result["summary"]
    assert "Fix users table schema constraints" in result["summary"]
    assert "shubh242/clinicops-copilot" in result["summary"]


@pytest.mark.anyio
async def test_agent_rag_project_prs():
    agent = Agent()
    result = await agent.run("Summarize open PRs for owner samuelcolvin and FastAPI Repository")
    
    # Should run RAG search first, then list open PRs for both pydantic and fastapi
    assert len(result["steps_executed"]) == 3
    assert result["steps_executed"][0]["tool"] == "rag_search"
    
    tools_called = {step["tool"] for step in result["steps_executed"]}
    assert "list_open_prs" in tools_called
    
    # Verify repos were resolved and queried
    pydantic_called = any(
        s["tool"] == "list_open_prs" and
        s["args"]["owner_name"] == "pydantic" and
        s["args"]["repo_name"] == "pydantic"
        for s in result["steps_executed"]
    )
    fastapi_called = any(
        s["tool"] == "list_open_prs" and
        s["args"]["owner_name"] == "fastapi" and
        s["args"]["repo_name"] == "fastapi"
        for s in result["steps_executed"]
    )
    assert pydantic_called
    assert fastapi_called
    
    # Verify response contains details from fallback mock PRs/real PRs and citations
    summary = result["summary"]
    assert "pydantic/pydantic" in summary
    assert "fastapi/fastapi" in summary
    assert "Citations" in summary
    assert "projects_metadata.md" in summary
