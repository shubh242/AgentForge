from pydantic import BaseModel, Field
from ..vector_store import QdrantVectorStore

class RAGSearchArgs(BaseModel):
    query: str = Field(..., description="The semantic search query to look up in the documentation.")
    limit: int = Field(2, description="The maximum number of matches to return.")

class RAGTool:
    def __init__(self) -> None:
        self._vector_store = None

    @property
    def vector_store(self) -> QdrantVectorStore:
        """Lazily initialize the Qdrant vector store only when needed."""
        if self._vector_store is None:
            self._vector_store = QdrantVectorStore()
        return self._vector_store

    async def rag_search(self, args: dict) -> list[dict]:
        """
        Search the documentation vector store for context.
        """
        validated = RAGSearchArgs(**args)
        return self.vector_store.search(query=validated.query, limit=validated.limit)
