from typing import List, Dict, Any, Optional
import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from fastapi import HTTPException
from .base import VectorDatabase


class QdrantAdapter(VectorDatabase):
    def __init__(self):
        self.name = "Qdrant"
        self.client = None
        self.host = os.getenv("QDRANT_HOST", "localhost")
        self.port = int(os.getenv("QDRANT_PORT", "6333"))

    async def connect(self) -> None:
        """Connect to Qdrant server"""
        try:
            # Create Qdrant client (uses HTTP by default)
            self.client = QdrantClient(
                host=self.host,
                port=self.port,
                timeout=60
            )

            # Test connection by getting health status
            health = self.client.get_health()
            print(f"Connected to Qdrant: {health}")

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"{self.name}: Failed to connect - {str(e)}"
            )

    async def create_collection(self, collection_name: str, dimension: int) -> None:
        """Create a collection for storing vectors with metadata"""
        if not self.client:
            await self.connect()

        try:
            # Delete collection if exists (for experimentation)
            collections = self.client.get_collections().collections
            if any(col.name == collection_name for col in collections):
                self.client.delete_collection(collection_name=collection_name)

            # Create collection with vector configuration
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=Distance.COSINE
                )
            )

            print(f"Created collection '{collection_name}' with dimension {dimension}")

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"{self.name}: Failed to create collection - {str(e)}"
            )

    async def insert(
        self,
        collection_name: str,
        vectors: List[List[float]],
        metadata: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> None:
        raise HTTPException(status_code=501, detail=f"{self.name}: insert not implemented")

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        raise HTTPException(status_code=501, detail=f"{self.name}: search not implemented")

    async def delete(
        self,
        collection_name: str,
        ids: List[str]
    ) -> None:
        raise HTTPException(status_code=501, detail=f"{self.name}: delete not implemented")

    async def disconnect(self) -> None:
        """Close the connection"""
        if self.client:
            self.client.close()
            print(f"Disconnected from Qdrant")