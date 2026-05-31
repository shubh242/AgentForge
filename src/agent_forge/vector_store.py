from pathlib import Path
import os
import time
import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

class QdrantVectorStore:
    def __init__(self) -> None:
        """
        Initialize the Qdrant client in memory, load HF credentials,
        and automatically seed/index the documentation corpus.
        """
        self.hf_token = os.environ.get("HF_TOKEN")
        if not self.hf_token:
            raise ValueError("HF_TOKEN is missing from environment. Application cannot run without it.")
        
        # Initialize in-memory Qdrant client
        self.client = QdrantClient(location=":memory:")
        self.collection_name = "documentation"
        self.offline_mode = False
        self.indexed_chunks = []
        
        # Setup collection and index documents
        self._init_collection()
        self.index_documents()

    def _init_collection(self) -> None:
        """Create the collection in Qdrant with all-MiniLM-L6-v2 vector configuration (384 dimensions)."""
        # Ensure we always create a fresh collection
        if self.client.collection_exists(self.collection_name):
            self.client.delete_collection(self.collection_name)
            
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )

    def get_embedding(self, text: str) -> list[float]:
        """
        Call the HuggingFace Inference API to get the embedding vector for the given text.
        Model: sentence-transformers/all-MiniLM-L6-v2
        Output size: 384 dimensions.
        """
        import hashlib
        url = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"
        headers = {"Authorization": f"Bearer {self.hf_token}"}
        payload = {"inputs": text}
        
        # Handle retries if HF returns 503 (model is loading)
        for attempt in range(5):
            try:
                response = httpx.post(url, headers=headers, json=payload, timeout=20.0)
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list):
                        if len(result) > 0 and isinstance(result[0], list):
                            return result[0]
                        return result
                    raise ValueError(f"Unexpected response format from HF Inference API: {result}")
                elif response.status_code == 503:
                    data = response.json()
                    wait_time = data.get("estimated_time", 5)
                    print(f"HF Model is loading, waiting {wait_time}s (attempt {attempt+1}/5)...")
                    time.sleep(wait_time)
                else:
                    raise RuntimeError(
                        f"HuggingFace API returned error {response.status_code}: {response.text}"
                    )
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.HTTPError) as e:
                # If network/DNS fails or token is invalid, fall back to offline deterministic hashing
                print(f"Warning: HuggingFace API call failed ({e}). Falling back to local offline mock embeddings.")
                self.offline_mode = True
                h = hashlib.sha256(text.encode('utf-8')).digest()
                vector = []
                for i in range(384):
                    byte_val = h[i % len(h)]
                    val = (byte_val / 255.0) * 2.0 - 1.0
                    vector.append(val)
                return vector
        raise RuntimeError("HuggingFace model failed to load after multiple retries.")

    def index_documents(self) -> None:
        """Read documents from docs/ directory, chunk them, and index them into Qdrant."""
        dir_path = Path(__file__).parent.parent.parent / "docs"
        if not dir_path.exists():
            dir_path = Path("docs")
            
        if not dir_path.exists():
            raise FileNotFoundError(f"docs directory not found at {dir_path.absolute()}")
            
        points = []
        point_idx = 0
        self.indexed_chunks = []
        for file_path in dir_path.glob("*.md"):
            content = file_path.read_text(encoding="utf-8")
            chunks = [chunk.strip() for chunk in content.split("\n\n") if chunk.strip()]
            
            for chunk in chunks:
                self.indexed_chunks.append({
                    "text": chunk,
                    "source": f"docs/{file_path.name}"
                })
                vector = self.get_embedding(chunk)
                points.append(
                    PointStruct(
                        id=point_idx,
                        vector=vector,
                        payload={"text": chunk, "source": f"docs/{file_path.name}"}
                    )
                )
                point_idx += 1
                
        if points:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )

    def search(self, query: str, limit: int = 2) -> list[dict]:
        """
        Search the collection for chunks similar to the query.
        Returns a list of matching dicts with 'text', 'source', and 'score'.
        """
        query_vector = self.get_embedding(query)
        
        # If offline_mode flag got set during embedding generation, use local keyword search
        if getattr(self, "offline_mode", False):
            scored_results = []
            query_lower = query.lower()
            query_words = set(query_lower.split())
            
            for item in self.indexed_chunks:
                text_lower = item["text"].lower()
                score = 0.0
                
                # Boost direct substring matches
                if query_lower in text_lower:
                    score += 10.0
                    
                # Score word overlap
                for word in query_words:
                    if word in text_lower:
                        score += 1.0
                        
                if score > 0.0:
                    scored_results.append({
                        "text": item["text"],
                        "source": item["source"],
                        "score": score
                    })
            
            scored_results.sort(key=lambda x: x["score"], reverse=True)
            return scored_results[:limit]
            
        search_result = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit
        )
        results = []
        for hit in search_result.points:
            results.append({
                "text": hit.payload.get("text"),
                "source": hit.payload.get("source"),
                "score": hit.score
            })
        return results
