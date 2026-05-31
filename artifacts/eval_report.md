# Evaluation Harness Report - Milestone 4

This report documents the quantitative performance metrics of the **AgentForge** orchestrator across a suite of 20 tasks, powered by a real-world **Groq Llama 3** model.

## Aggregated Performance Summary

| Metric | Value |
|---|---|
| **Total Scenarios** | 20 |
| **Task Success Rate** | **45.0%** |
| **Average Tool Call F1 Score** | **63.7%** |
| **Mean Latency** | 19.06s |
| **p95 Latency** | 45.78s |
| **Total Evaluation Cost** | $0.028139 |
| **Average Cost per Task** | $0.001407 |

---

## Detailed Scenario Breakdown

| Scenario ID | Category | Task | Expected Tools | Actual Tools | Tool F1 | Success | Latency | Cost |
|---|---|---|---|---|---|---|---|---|
| `scenario_1` | `misc` | "Verify connection" | `rag_search, postgres_query` | `postgres_query` | 0.67 | ✅ Pass | 0.63s | $0.000941 |
| `scenario_2` | `db_only` | "Show me the users table schema" | `rag_search, postgres_query` | `postgres_query, postgres_query, postgres_query, postgres_query, postgres_query` | 0.67 | ✅ Pass | 1.33s | $0.002906 |
| `scenario_3` | `github_only` | "Show me the file contents of README.md" | `rag_search, get_file_contents` | `get_file_contents, postgres_query` | 0.50 | ✅ Pass | 11.66s | $0.001496 |
| `scenario_4` | `multi_step` | "Summarize open PRs for owner samuelcolvin and FastAPI Repository" | `rag_search, list_open_prs` | `rag_search, list_open_prs` | 1.00 | ❌ Fail | 24.89s | $0.001658 |
| `scenario_5` | `github_only` | "List open PRs for pydantic/pydantic" | `rag_search, list_open_prs` | `None` | 0.00 | ✅ Pass | 8.46s | $0.000000 |
| `scenario_6` | `multi_step` | "Identify open PRs for Samuel Colvin" | `rag_search, list_open_prs` | `rag_search, list_open_prs` | 1.00 | ❌ Fail | 17.83s | $0.001135 |
| `scenario_7` | `multi_step` | "Find lead developer of FastAPI and list open PRs" | `rag_search, list_open_prs` | `rag_search, list_open_prs` | 1.00 | ❌ Fail | 37.79s | $0.002226 |
| `scenario_8` | `multi_step` | "Summarize open PRs touching the users table" | `rag_search, postgres_query, list_open_prs` | `postgres_query, postgres_query` | 0.50 | ❌ Fail | 20.78s | $0.001459 |
| `scenario_9` | `rag_only` | "Check documentation for database guide" | `rag_search` | `rag_search, postgres_query, postgres_query, postgres_query` | 0.67 | ✅ Pass | 18.54s | $0.001584 |
| `scenario_10` | `rag_only` | "Find project developer configurations for active repositories" | `rag_search` | `rag_search, postgres_query` | 0.67 | ❌ Fail | 27.63s | $0.001618 |
| `scenario_11` | `multi_step` | "Triage open PRs for Hanh Nguyen's project TrackerApp" | `rag_search, list_open_prs` | `rag_search, list_open_prs` | 1.00 | ❌ Fail | 16.25s | $0.001012 |
| `scenario_12` | `multi_step` | "List open PRs for Parth Gala's dropshipping alien" | `rag_search, list_open_prs` | `list_open_prs, postgres_query, postgres_query, postgres_query, postgres_query` | 0.50 | ❌ Fail | 47.95s | $0.002802 |
| `scenario_13` | `multi_step` | "List open PRs for vichcraft's project ccas" | `rag_search, list_open_prs` | `list_open_prs, postgres_query` | 0.50 | ✅ Pass | 24.41s | $0.001440 |
| `scenario_14` | `rag_only` | "Search docs for FastAPI owner details" | `rag_search` | `rag_search` | 1.00 | ✅ Pass | 15.14s | $0.001023 |
| `scenario_15` | `rag_only` | "Look up database guide details for users table" | `rag_search` | `rag_search, postgres_query` | 0.67 | ✅ Pass | 18.36s | $0.001085 |
| `scenario_16` | `db_only` | "Show database schema of pull_requests table" | `rag_search, postgres_query` | `None` | 0.00 | ❌ Fail | 6.45s | $0.000000 |
| `scenario_17` | `rag_only` | "Check active developer email for pydantic lead" | `rag_search` | `rag_search, postgres_query` | 0.67 | ❌ Fail | 5.85s | $0.001143 |
| `scenario_18` | `db_only` | "Query SQLite database for pull request count" | `rag_search, postgres_query` | `postgres_query` | 0.67 | ❌ Fail | 16.91s | $0.000917 |
| `scenario_19` | `github_only` | "Show content of projects_metadata.md" | `rag_search, get_file_contents` | `get_file_contents` | 0.67 | ✅ Pass | 14.65s | $0.000959 |
| `scenario_20` | `rag_only` | "Find description of dropshipping alien repo" | `rag_search` | `rag_search, postgres_query, postgres_query, list_open_prs, get_file_contents` | 0.40 | ❌ Fail | 45.78s | $0.002735 |
