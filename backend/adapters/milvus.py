from typing import List, Dict, Any, Optional
import os
from fastapi import HTTPException
from pymilvus import MilvusClient, connections
from .base import VectorDatabase


class MilvusAdapter(VectorDatabase):
    def __init__(self):
        self.name = "Milvus"
        self.client: Optional[MilvusClient] = None
        self.host = os.getenv("MILVUS_HOST", "localhost")
        self.port = int(os.getenv("MILVUS_PORT", "19530"))
        self.alias = "default"

    async def connect(self) -> None:
        """Connect to Milvus and verify connection"""
        try:
            # Create MilvusClient for simpler API
            uri = f"http://{self.host}:{self.port}"
            self.client = MilvusClient(uri=uri)

            # Verify connection by listing collections
            collections = self.client.list_collections()
            print(f"Connected to Milvus at {self.host}:{self.port} (collections: {len(collections)})")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to connect to Milvus: {str(e)}")

    async def create_collection(self, collection_name: str, dimension: int) -> None:
        """Create a Milvus collection for vector search"""
        if not self.client:
            raise HTTPException(status_code=500, detail="Not connected to Milvus")

        try:
            # Drop existing collection if it exists
            if self.client.has_collection(collection_name):
                self.client.drop_collection(collection_name)
                print(f"Dropped existing collection: {collection_name}")

            # Create collection with MilvusClient's simple API
            # This automatically creates id (primary key), vector, and any other fields
            self.client.create_collection(
                collection_name=collection_name,
                dimension=dimension,
                metric_type="COSINE",  # Use cosine similarity
                index_type="HNSW",     # HNSW index for fast ANN search
                params={
                    "M": 16,           # Number of connections per layer
                    "efConstruction": 200  # Size of dynamic candidate list for construction
                }
            )

            print(f"Created Milvus collection: {collection_name} with dimension {dimension}")

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create collection: {str(e)}")

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
        """Disconnect from Milvus"""
        try:
            if self.client:
                self.client.close()
                self.client = None
                print(f"Disconnected from Milvus")
        except Exception as e:
            print(f"Error disconnecting from Milvus: {str(e)}")