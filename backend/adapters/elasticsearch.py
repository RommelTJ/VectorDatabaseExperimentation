from typing import List, Dict, Any, Optional
import os
from fastapi import HTTPException
from elasticsearch import AsyncElasticsearch
from .base import VectorDatabase


class ElasticsearchAdapter(VectorDatabase):
    def __init__(self):
        self.name = "Elasticsearch"
        self.client: Optional[AsyncElasticsearch] = None
        self.host = os.getenv("ELASTICSEARCH_HOST", "localhost")
        self.port = int(os.getenv("ELASTICSEARCH_PORT", "9200"))

    async def connect(self) -> None:
        """Connect to Elasticsearch and verify connection"""
        try:
            self.client = AsyncElasticsearch(
                hosts=[f"http://{self.host}:{self.port}"],
                request_timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )
            # Verify connection by checking cluster health
            health = await self.client.cluster.health()
            print(f"Connected to Elasticsearch at {self.host}:{self.port} (status: {health['status']})")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to connect to Elasticsearch: {str(e)}")

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
        """Close Elasticsearch connection"""
        if self.client:
            await self.client.close()
            print("Disconnected from Elasticsearch")