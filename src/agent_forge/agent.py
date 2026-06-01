from dataclasses import dataclass
import re
import os
import json
import sys
from typing import Any
from dotenv import load_dotenv

from .tools.postgres_tool import PostgresQueryTool
from .tools.github_tool import GithubTool
from .tools.rag_tool import RAGTool

load_dotenv()


@dataclass
class ToolCall:
    tool: str
    args: dict[str, Any]


class Agent:
    def __init__(self, use_llm: bool = True) -> None:
        self.postgres = PostgresQueryTool()
        self.github = GithubTool()
        self.rag = RAGTool()

        self.groq_api_key = os.environ.get("GROQ_API_KEY")
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.use_llm = use_llm

        if self.groq_api_key:
            from groq import Groq
            self.llm_client = Groq(api_key=self.groq_api_key)
            self.model = "llama-3.1-8b-instant"
        elif self.openai_api_key:
            from openai import OpenAI
            self.llm_client = OpenAI(api_key=self.openai_api_key)
            self.model = "gpt-4o-mini"
        else:
            self.llm_client = None
            self.model = None

    def get_tool_definitions(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "postgres_query",
                    "description": "Execute a read-only SELECT SQL query on the database. Tables: 'users' (id, name, email, created_at), 'pull_requests' (id, repo, title, author, status, created_at). Note that the 'repo' column contains the full 'owner/repo' path (e.g. 'shubh242/clinicops-copilot').",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The read-only SELECT query. E.g. SELECT * FROM pull_requests WHERE status = 'open'"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_open_prs",
                    "description": "List the open Pull Requests for a given GitHub repository. Returns list of PRs with title, state, user, html_url.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "owner_name": {
                                "type": "string",
                                "description": "The GitHub owner/organization name."
                            },
                            "repo_name": {
                                "type": "string",
                                "description": "The repository name."
                            }
                        },
                        "required": ["owner_name", "repo_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_file_contents",
                    "description": "Get the file contents of a specific file in a GitHub repository.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "owner_name": {
                                "type": "string",
                                "description": "The GitHub owner/organization name."
                            },
                            "repo_name": {
                                "type": "string",
                                "description": "The repository name."
                            },
                            "file_path": {
                                "type": "string",
                                "description": "The relative path to the file in the repository."
                            }
                        },
                        "required": ["owner_name", "repo_name", "file_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "rag_search",
                    "description": "Search the local documentation vector store for context, repository metadata, database schemas, and developer directories. ALWAYS call this first when resolving namespaces, project ownership, or documentation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query to look up."
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

    async def run(self, task: str) -> dict[str, Any]:
        """
        Execute the planning loop: plan -> pick tool -> call -> observe -> repeat
        until done. Uses LLM tool calling.
        """
        if not self.llm_client:
            raise ValueError("No LLM API key provided. AgentForge requires a configured GROQ_API_KEY or OPENAI_API_KEY.")

        print(f"The requested task is: {task}")
        history = []
        max_steps = 5
        total_prompt_tokens = 0
        total_completion_tokens = 0

        system_prompt = (
            "You are AgentForge, a developer productivity assistant. "
            "Help the developer with their task by using the provided tools. "
            "Always call `rag_search` first if you need to look up documentation, resolve repo owners, project configurations, or database schemas. "
            "Respond only with the final synthesized answer once all tools are completed."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task}
        ]

        steps_executed = []

        for step in range(max_steps):
            import time
            import re
            
            response = None
            max_retries = 5
            for retry_attempt in range(max_retries):
                try:
                    response = self.llm_client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=self.get_tool_definitions(),
                        tool_choice="auto",
                        temperature=0.0
                    )
                    break
                except Exception as e:
                    err_msg = str(e)
                    is_rate_limit = False
                    
                    if hasattr(e, "status_code") and e.status_code == 429:
                        is_rate_limit = True
                    elif "429" in err_msg or "rate limit" in err_msg.lower() or "tpm" in err_msg.lower():
                        is_rate_limit = True
                        
                    if is_rate_limit and retry_attempt < max_retries - 1:
                        wait_seconds = 2.0
                        match = re.search(r"try again in (\d+(?:\.\d+)?)s", err_msg)
                        if match:
                            try:
                                wait_seconds = float(match.group(1)) + 0.5
                            except ValueError:
                                pass
                        else:
                            wait_seconds = 2.0 ** (retry_attempt + 1)
                            
                        print(f"Rate limit hit (429). Retrying in {wait_seconds:.2f} seconds... (Attempt {retry_attempt + 1}/{max_retries})")
                        time.sleep(wait_seconds)
                    else:
                        print(f"LLM call failed: {e}")
                        return {
                            "task": task,
                            "steps_executed": steps_executed,
                            "summary": f"Failed to complete task due to LLM error: {e}",
                            "usage": {
                                "prompt_tokens": total_prompt_tokens,
                                "completion_tokens": total_completion_tokens,
                                "total_tokens": total_prompt_tokens + total_completion_tokens
                            },
                            "data": {"error": str(e)}
                        }

            if response is None:
                return {
                    "task": task,
                    "steps_executed": steps_executed,
                    "summary": "Failed to complete task: LLM did not return a response after multiple retries.",
                    "usage": {
                        "prompt_tokens": total_prompt_tokens,
                        "completion_tokens": total_completion_tokens,
                        "total_tokens": total_prompt_tokens + total_completion_tokens
                    },
                    "data": {"error": "LLM did not return a response after multiple retries."}
                }

            if getattr(response, "usage", None):
                total_prompt_tokens += getattr(response.usage, "prompt_tokens", 0)
                total_completion_tokens += getattr(response.usage, "completion_tokens", 0)

            choice = response.choices[0]
            message = choice.message
            
            messages.append(message)

            if not getattr(message, "tool_calls", None):
                return {
                    "task": task,
                    "steps_executed": steps_executed,
                    "summary": message.content or "",
                    "usage": {
                        "prompt_tokens": total_prompt_tokens,
                        "completion_tokens": total_completion_tokens,
                        "total_tokens": total_prompt_tokens + total_completion_tokens
                    },
                    "data": {}
                }

            seen_calls_this_turn = set()
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    tool_args = json.loads(tool_call.function.arguments)
                except Exception:
                    tool_args = {}

                # Coerce 'limit' to integer in rag_search
                if tool_name == "rag_search":
                    if "limit" in tool_args:
                        try:
                            tool_args["limit"] = int(tool_args["limit"])
                        except (ValueError, TypeError):
                            tool_args["limit"] = 2

                # Deduplicate within the same response turn
                try:
                    norm_args = json.dumps(tool_args, sort_keys=True)
                except Exception:
                    norm_args = str(tool_args)
                sig = (tool_name, norm_args)
                
                if sig in seen_calls_this_turn:
                    # Skip duplicate tool calls in the same turn
                    print(f"Skipping duplicate tool call in the same turn: {tool_name} with {tool_args}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": json.dumps({"error": "Duplicate tool call in the same turn. Result omitted."})
                    })
                    continue
                seen_calls_this_turn.add(sig)

                # Check if this tool call has been executed in a previous turn
                prev_match = None
                occurrences = 0
                for prev in steps_executed:
                    try:
                        prev_norm = json.dumps(prev["args"], sort_keys=True)
                    except Exception:
                        prev_norm = str(prev["args"])
                    if prev["tool"] == tool_name and prev_norm == norm_args:
                        prev_match = prev
                        occurrences += 1

                if occurrences >= 2:
                    # If called more than twice, intercept with an explicit warning/guidance to the model
                    print(f"Intercepting repeated tool call to prevent infinite loop: {tool_name} with {tool_args}")
                    result = {
                        "error": (
                            f"You have already called '{tool_name}' with these arguments {tool_args} {occurrences} times. "
                            "It has returned the same result. Please do not call it again. "
                            "Verify if you are using the correct repository coordinates (e.g. 'shubh242/clinicops-copilot' instead of 'clinicops-copilot'), "
                            "or check the documentation/schemas using 'rag_search'."
                        )
                    }
                    status = "error"
                elif prev_match is not None:
                    # Reuse cached result to avoid redundant network/database execution
                    print(f"Reusing cached result for tool call: {tool_name} with {tool_args}")
                    result = prev_match["result"]
                    status = prev_match["status"]
                else:
                    print(f"Step {len(steps_executed) + 1}: Planning to call tool '{tool_name}' with args {tool_args}")
                    try:
                        result = await self.call_tool(ToolCall(tool=tool_name, args=tool_args))
                        status = "success"
                    except Exception as e:
                        result = {"error": str(e)}
                        status = "error"

                steps_executed.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "status": status,
                    "result": result
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": json.dumps(result)
                })

        return {
            "task": task,
            "steps_executed": steps_executed,
            "summary": "Maximum execution steps reached without a final response.",
            "usage": {
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "total_tokens": total_prompt_tokens + total_completion_tokens
            },
            "data": {}
        }

    async def call_tool(self, decision: ToolCall) -> dict[str, Any]:
        if decision.tool == "postgres_query":
            return await self.postgres.run(decision.args)

        if decision.tool == "list_open_prs":
            return await self.github.list_open_prs(decision.args)

        if decision.tool == "get_file_contents":
            return await self.github.get_file_contents(decision.args)

        if decision.tool == "rag_search":
            return await self.rag.rag_search(decision.args)

        raise ValueError(f"Unknown tool: {decision.tool}")