from typing import Any

from pydantic import BaseModel, field_validator

from ..db import get_connection

FORBIDDEN_SQL_KEYWORDS = [
    "insert",
    "update",
    "delete",
    "create",
    "alter",
    "drop",
    "truncate",
    "grant",
    "revoke",
    "copy",
    "commit",
    "rollback",
    "replace",
    "merge",
    "execute",
    "call",
]


class PostgresQueryArgs(BaseModel):
    query: str

    @field_validator("query")
    @classmethod
    def validate_read_only(cls, value: str) -> str:
        """Validating read-only SQL content."""
        normalized = value.strip().lower()
        if not normalized.startswith("select"):
            raise ValueError("Only SELECT queries are allowed.")

        for keyword in FORBIDDEN_SQL_KEYWORDS:
            if keyword in normalized and not normalized.startswith(keyword):
                raise ValueError(f"Forbidden SQL keyword in query: {keyword}")

        return value


class PostgresQueryTool:
    async def run(self, args: dict[str, Any]) -> dict[str, Any]:
        payload = PostgresQueryArgs(**args)
        return await self._execute(payload.query)

    async def _execute(self, query: str) -> dict[str, Any]:
        """Execute a read-only SQL query using SQLite."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            print(query)
            cursor.execute(query)
            rows = [dict(row) for row in cursor.fetchall()]
            return {
                "tool": "postgres_query",
                "query": query,
                "row_count": len(rows),
                "rows": rows,
            }
        except Exception as ex:
            raise SyntaxError(f"Enter a Valid Query {ex}" )
        finally:
            conn.close()
