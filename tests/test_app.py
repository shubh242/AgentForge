from fastapi.testclient import TestClient

from agent_forge.main import app
from agent_forge.agent import Agent

client = TestClient(app)


def test_health():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_tools():
    response = client.get("/mcp/tools")
    assert response.status_code == 200
    assert response.json()[0]["name"] == "postgres_query"


def test_unknown_tool():
    response = client.post("/mcp/call", json={"tool": "unknown", "args": {}})
    assert response.status_code == 404


def test_postgres_query_select():
    """Test running a SELECT query through the MCP endpoint."""
    response = client.post(
        "/mcp/call",
        json={"tool": "postgres_query", "args": {"query": "SELECT COUNT(*) as count FROM users"}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tool"] == "postgres_query"
    assert data["row_count"] > 0
    assert "rows" in data
    assert data["rows"][0]["count"] >= 3  # We inserted 3 users


def test_postgres_query_rejected():
    """Test that non-SELECT queries are rejected."""
    response = client.post(
        "/mcp/call",
        json={"tool": "postgres_query", "args": {"query": "DELETE FROM users"}},
    )
    assert response.status_code == 422  # Validation error
