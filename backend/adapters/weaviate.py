from typing import List, Dict, Any, Optional
import os
import weaviate
from weaviate.classes.config import Configure
from fastapi import HTTPException
from .base import VectorDatabase


class WeaviateAdapter(VectorDatabase):
    def __init__(self):
        self.name = "Weaviate"
        self.client = None
        self.host = os.getenv("WEAVIATE_HOST", "localhost")
        self.port = int(os.getenv("WEAVIATE_PORT", "8080"))

    async def connect(self) -> None:
        """Connect to Weaviate server"""
        try:
            # Connect to Weaviate using v4 client API
            self.client = weaviate.connect_to_local(
                host=self.host,
                port=self.port
            )

            # Test connection by checking if client is ready
            if self.client.is_ready():
                print(f"Connected to Weaviate at {self.host}:{self.port}")
            else:
                raise Exception("Weaviate is not ready")

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"{self.name}: Failed to connect - {str(e)}"
            )

    async def create_collection(self, collection_name: str, dimension: int) -> None:
        raise HTTPException(status_code=501, detail=f"{self.name}: create_collection not implemented")

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
        """Close the connection to Weaviate"""
        if self.client:
            self.client.close()
            print(f"Disconnected from Weaviate")