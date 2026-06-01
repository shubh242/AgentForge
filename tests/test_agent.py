import pytest
from unittest.mock import MagicMock, AsyncMock
from agent_forge.agent import Agent, ToolCall


class MockCompletionUsage:
    def __init__(self, prompt_tokens=10, completion_tokens=10):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class MockFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class MockToolCall:
    def __init__(self, id, name, arguments):
        self.id = id
        self.function = MockFunction(name, arguments)


class MockMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []
        self.role = "assistant"


class MockChoice:
    def __init__(self, message):
        self.message = message


class MockCompletionResponse:
    def __init__(self, content=None, tool_calls=None, prompt_tokens=10, completion_tokens=10):
        self.choices = [MockChoice(MockMessage(content, tool_calls))]
        self.usage = MockCompletionUsage(prompt_tokens, completion_tokens)


@pytest.mark.anyio
async def test_agent_plan_ping():
    agent = Agent()
    agent.model = "mock-model"
    
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        MockCompletionResponse(tool_calls=[MockToolCall("tc1", "rag_search", '{"query": "Verify connection"}')]),
        MockCompletionResponse(tool_calls=[MockToolCall("tc2", "postgres_query", '{"query": "SELECT 1 AS ping"}')]),
        MockCompletionResponse(content="No open Pull Requests found and database is connected.")
    ]
    agent.llm_client = mock_client

    result = await agent.run("Verify connection")
    assert len(result["steps_executed"]) == 2
    assert result["steps_executed"][0]["tool"] == "rag_search"
    assert result["steps_executed"][1]["tool"] == "postgres_query"
    assert result["steps_executed"][1]["args"]["query"] == "SELECT 1 AS ping"
    assert "No open Pull Requests" in result["summary"]


@pytest.mark.anyio
async def test_agent_plan_database_query():
    agent = Agent()
    agent.model = "mock-model"
    
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        MockCompletionResponse(tool_calls=[MockToolCall("tc1", "rag_search", '{"query": "Show me the users table schema"}')]),
        MockCompletionResponse(tool_calls=[MockToolCall("tc2", "postgres_query", '{"query": "SELECT * FROM users LIMIT 1"}')]),
        MockCompletionResponse(content="Here is the users table schema.")
    ]
    agent.llm_client = mock_client

    result = await agent.run("Show me the users table schema")
    assert len(result["steps_executed"]) == 2
    assert result["steps_executed"][0]["tool"] == "rag_search"
    assert result["steps_executed"][1]["tool"] == "postgres_query"
    assert "users" in result["steps_executed"][1]["args"]["query"]


@pytest.mark.anyio
async def test_agent_plan_github_file_contents():
    agent = Agent()
    agent.model = "mock-model"
    
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        MockCompletionResponse(tool_calls=[MockToolCall("tc1", "rag_search", '{"query": "Show me the file contents of README.md"}')]),
        MockCompletionResponse(tool_calls=[MockToolCall("tc2", "get_file_contents", '{"owner_name": "shubh242", "repo_name": "clinicops-copilot", "file_path": "README.md"}')]),
        MockCompletionResponse(content="Mock file content for README.md.")
    ]
    agent.llm_client = mock_client

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
    agent.model = "mock-model"
    
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        MockCompletionResponse(tool_calls=[MockToolCall("tc1", "rag_search", '{"query": "Summarize open PRs touching the users table"}')]),
        MockCompletionResponse(tool_calls=[MockToolCall("tc2", "postgres_query", '{"query": "SELECT * FROM pull_requests WHERE status = \'open\'"}')]),
        MockCompletionResponse(tool_calls=[MockToolCall("tc3", "list_open_prs", '{"owner_name": "shubh242", "repo_name": "clinicops-copilot"}')]),
        MockCompletionResponse(content="Found 1 open Pull Request(s) touching the users table: 'Fix users table schema constraints' (repo: shubh242/clinicops-copilot).")
    ]
    agent.llm_client = mock_client
    
    agent.github.list_open_prs = AsyncMock(return_value=[
        {
            "number": 5,
            "title": "Fix users table schema constraints",
            "state": "open",
            "user": {"login": "shubh242"},
            "html_url": "https://github.com/shubh242/clinicops-copilot/pull/5"
        }
    ])

    result = await agent.run("Summarize open PRs touching the users table")
    
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
    
    assert "open Pull Request(s)" in result["summary"]
    assert "Fix users table schema constraints" in result["summary"]
    assert "shubh242/clinicops-copilot" in result["summary"]


@pytest.mark.anyio
async def test_agent_rag_project_prs():
    agent = Agent()
    agent.model = "mock-model"
    
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        MockCompletionResponse(tool_calls=[MockToolCall("tc1", "rag_search", '{"query": "Summarize open PRs for owner samuelcolvin and FastAPI Repository"}')]),
        MockCompletionResponse(tool_calls=[
            MockToolCall("tc2", "list_open_prs", '{"owner_name": "pydantic", "repo_name": "pydantic"}'),
            MockToolCall("tc3", "list_open_prs", '{"owner_name": "fastapi", "repo_name": "fastapi"}')
        ]),
        MockCompletionResponse(content="Summarized open PRs for pydantic/pydantic and fastapi/fastapi. Citations: projects_metadata.md")
    ]
    agent.llm_client = mock_client
    
    agent.github.list_open_prs = AsyncMock(side_effect=lambda args: [
        {
            "number": 9000 if args["owner_name"] == "pydantic" else 11523,
            "title": "Mock PR title"
        }
    ])

    result = await agent.run("Summarize open PRs for owner samuelcolvin and FastAPI Repository")
    
    assert len(result["steps_executed"]) == 3
    assert result["steps_executed"][0]["tool"] == "rag_search"
    
    tools_called = {step["tool"] for step in result["steps_executed"]}
    assert "list_open_prs" in tools_called
    
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
    
    summary = result["summary"]
    assert "pydantic/pydantic" in summary
    assert "fastapi/fastapi" in summary
