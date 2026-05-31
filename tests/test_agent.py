import pytest
from agent_forge.agent import Agent, ToolCall


@pytest.mark.anyio
async def test_agent_plan_ping():
    agent = Agent()
    # Task doesn't match any specific patterns, should fallback to ping
    result = await agent.run("Verify connection")
    assert len(result["steps_executed"]) == 1
    assert result["steps_executed"][0]["tool"] == "postgres_query"
    assert result["steps_executed"][0]["args"]["query"] == "SELECT 1 AS ping"
    assert "No open Pull Requests" in result["summary"]


@pytest.mark.anyio
async def test_agent_plan_database_query():
    agent = Agent()
    # Task asks about schema
    result = await agent.run("Show me the users table schema")
    assert len(result["steps_executed"]) == 1
    assert result["steps_executed"][0]["tool"] == "postgres_query"
    assert "users" in result["steps_executed"][0]["args"]["query"]


@pytest.mark.anyio
async def test_agent_plan_github_file_contents():
    agent = Agent()
    # Task asks for file contents
    result = await agent.run("Show me the file contents of README.md")
    assert len(result["steps_executed"]) == 1
    assert result["steps_executed"][0]["tool"] == "get_file_contents"
    assert result["steps_executed"][0]["args"]["owner_name"] == "shubh242"
    assert result["steps_executed"][0]["args"]["repo_name"] == "clinicops-copilot"
    assert result["steps_executed"][0]["args"]["file_path"] == "README.md"


@pytest.mark.anyio
async def test_agent_loop_open_prs_touching_users_table():
    agent = Agent()
    # Task asks for open PRs touching the users table
    result = await agent.run("Summarize open PRs touching the users table")
    
    # It should have executed 2 steps:
    # 1. postgres_query to list open PRs
    # 2. list_open_prs on the repo containing 'users' (shubh242/clinicops-copilot)
    assert len(result["steps_executed"]) == 2
    
    step1 = result["steps_executed"][0]
    assert step1["tool"] == "postgres_query"
    assert "status = 'open'" in step1["args"]["query"]
    
    step2 = result["steps_executed"][1]
    assert step2["tool"] == "list_open_prs"
    assert step2["args"]["owner_name"] == "shubh242"
    assert step2["args"]["repo_name"] == "clinicops-copilot"
    
    # Verify synthesized response has the PR details
    assert "open Pull Request(s)" in result["summary"]
    assert "Fix users table schema constraints" in result["summary"]
    assert "shubh242/clinicops-copilot" in result["summary"]
