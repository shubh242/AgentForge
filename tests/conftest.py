import pytest
import hashlib
from unittest.mock import patch
from agent_forge.vector_store import QdrantVectorStore

@pytest.fixture(autouse=True)
def mock_get_embedding():
    def get_mock_vector(text: str) -> list[float]:
        # Generate a deterministic 384-dimensional vector based on the input text hash
        h = hashlib.sha256(text.encode('utf-8')).digest()
        # Repeat/expand the 32-byte hash to 384 dimensions
        vector = []
        for i in range(384):
            byte_val = h[i % len(h)]
            # Normalize to float between -1.0 and 1.0
            val = (byte_val / 255.0) * 2.0 - 1.0
            vector.append(val)
        return vector

    with patch.object(QdrantVectorStore, 'get_embedding', side_effect=get_mock_vector) as mock:
        yield mock
