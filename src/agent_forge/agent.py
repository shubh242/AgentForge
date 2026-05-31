from dataclasses import dataclass
from typing import Any

from .tools.postgres_tool import PostgresQueryTool
from .tools.github_tool import GithubTool


@dataclass
class ToolCall:
    tool: str
    args: dict[str, Any]


class Agent:
    def __init__(self) -> None:
        self.postgres = PostgresQueryTool()
        self.github = GithubTool()

    def plan(self, task: str, history: list[dict[str, Any]]) -> ToolCall | None:
        """
        Stateful planner that makes a decision based on the task and execution history.
        This rule-based planner supports multi-step orchestrations for Milestone 2.
        """
        task_lower = task.lower()

        # Step 1: Detect already executed tools to prevent duplicate calls
        executed_tools = {step["tool"] for step in history}

        # Case A: Task asks to summarize open pull requests touching users table
        if ("open pr" in task_lower or "pull request" in task_lower) and ("users" in task_lower or "schema" in task_lower):
            # 1. First run a database query to find open PRs in our records
            if "postgres_query" not in executed_tools:
                return ToolCall(
                    tool="postgres_query",
                    args={"query": "SELECT * FROM pull_requests WHERE status = 'open'"}
                )

            # 2. Inspect the database result to find which repository has PRs touching the users table
            pg_result = next((step["result"] for step in history if step.get("tool") == "postgres_query" and "result" in step), None)
            if pg_result and "rows" in pg_result:
                for row in pg_result["rows"]:
                    title = row.get("title", "").lower()
                    repo = row.get("repo", "").lower()
                    if "users" in title or "users" in repo:
                        parts = row["repo"].split("/")
                        if len(parts) == 2:
                            owner_name, repo_name = parts
                            # Check if we already fetched PR details from GitHub for this repo
                            already_fetched = any(
                                s.get("tool") == "list_open_prs" and
                                s.get("args", {}).get("owner_name") == owner_name and
                                s.get("args", {}).get("repo_name") == repo_name
                                for s in history
                            )
                            if not already_fetched:
                                return ToolCall(
                                    tool="list_open_prs",
                                    args={"owner_name": owner_name, "repo_name": repo_name}
                                )

            # If we've done the DB query and fetched from GitHub (or no matching repo found), we're done
            return None

        # Case B: Task asks about pull requests in general
        if "open pr" in task_lower or "pull request" in task_lower:
            if "list_open_prs" not in executed_tools:
                # Default to shubh242/clinicops-copilot if not specified
                return ToolCall(
                    tool="list_open_prs",
                    args={"owner_name": "shubh242", "repo_name": "clinicops-copilot"}
                )
            return None

        # Case C: Task asks about database schema or user table specifically
        if "schema" in task_lower or "users table" in task_lower:
            if "postgres_query" not in executed_tools:
                return ToolCall(
                    tool="postgres_query",
                    args={"query": "SELECT name, email FROM users LIMIT 10"}
                )
            return None

        # Case D: Task asks for file contents
        if "file contents" in task_lower or "show me" in task_lower:
            if "get_file_contents" not in executed_tools:
                return ToolCall(
                    tool="get_file_contents",
                    args={"owner_name": "shubh242", "repo_name": "clinicops-copilot", "file_path": "README.md"}
                )
            return None

        # Fallback ping query if history is empty
        if not history:
            return ToolCall(
                tool="postgres_query",
                args={"query": "SELECT 1 AS ping"}
            )

        return None

    async def run(self, task: str) -> dict[str, Any]:
        """
        Execute the planning loop: plan -> pick tool -> call -> observe -> repeat
        until done.
        """
        print(f"The requested task is: {task}")
        history = []
        max_steps = 5

        for step in range(max_steps):
            decision = self.plan(task, history)
            if decision is None:
                break

            print(f"Step {step + 1}: Planning to call tool '{decision.tool}' with args {decision.args}")
            try:
                result = await self.call_tool(decision)
                history.append({
                    "tool": decision.tool,
                    "args": decision.args,
                    "result": result
                })
            except Exception as e:
                print(f"Error calling tool '{decision.tool}': {e}")
                history.append({
                    "tool": decision.tool,
                    "args": decision.args,
                    "error": str(e)
                })

        # Synthesize final answer based on execution history
        return self.synthesize_answer(task, history)

    def synthesize_answer(self, task: str, history: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Synthesize the execution history into a final summary response.
        """
        open_prs_touching_users = []

        for step in history:
            # Gather open PRs matching criteria from DB query
            if step.get("tool") == "postgres_query" and "result" in step:
                rows = step["result"].get("rows", [])
                for row in rows:
                    title = row.get("title", "").lower()
                    repo = row.get("repo", "").lower()
                    status = row.get("status", "").lower()
                    if status == "open" and ("users" in title or "users" in repo):
                        open_prs_touching_users.append({
                            "title": row.get("title"),
                            "repo": row.get("repo"),
                            "author": row.get("author"),
                            "status": row.get("status")
                        })

            # Gather open PRs matching criteria from GitHub tool
            if step.get("tool") == "list_open_prs" and "result" in step:
                prs = step["result"]
                if isinstance(prs, list):
                    for pr in prs:
                        title = pr.get("title", "").lower()
                        state = pr.get("state", pr.get("status", "")).lower()
                        if "users" in title and (state == "open" or not state):
                            # Avoid duplicate records
                            if not any(item["title"] == pr.get("title") for item in open_prs_touching_users):
                                author = pr.get("user", {}).get("login") if isinstance(pr.get("user"), dict) else pr.get("author")
                                open_prs_touching_users.append({
                                    "title": pr.get("title"),
                                    "repo": f"{step['args']['owner_name']}/{step['args']['repo_name']}",
                                    "author": author or pr.get("user"),
                                    "status": state or "open"
                                })

        # Construct markdown summary
        if open_prs_touching_users:
            summary = f"Found {len(open_prs_touching_users)} open Pull Request(s) touching the users table:\n"
            for i, pr in enumerate(open_prs_touching_users, 1):
                summary += f"{i}. '{pr['title']}' (repo: {pr['repo']}, author: {pr['author']}, status: {pr['status']})\n"
        else:
            summary = "No open Pull Requests touching the users table were found."

        return {
            "task": task,
            "steps_executed": [
                {
                    "tool": step["tool"],
                    "args": step["args"],
                    "status": "success" if "result" in step else "error"
                }
                for step in history
            ],
            "summary": summary,
            "data": {
                "open_prs": open_prs_touching_users
            }
        }

    async def call_tool(self, decision: ToolCall) -> dict[str, Any]:
        if decision.tool == "postgres_query":
            return await self.postgres.run(decision.args)

        if decision.tool == "list_open_prs":
            return await self.github.list_open_prs(decision.args)

        if decision.tool == "get_file_contents":
            return await self.github.get_file_contents(decision.args)

        raise ValueError(f"Unknown tool: {decision.tool}")