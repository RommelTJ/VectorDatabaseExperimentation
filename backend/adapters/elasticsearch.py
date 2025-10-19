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
        """Create an Elasticsearch index for vector search"""
        if not self.client:
            raise HTTPException(status_code=500, detail="Not connected to Elasticsearch")

        try:
            # Delete existing index if it exists
            if await self.client.indices.exists(index=collection_name):
                await self.client.indices.delete(index=collection_name)
                print(f"Deleted existing index: {collection_name}")

            # Create index with vector field and metadata fields
            # Using dense_vector field type with cosine similarity
            index_body = {
                "mappings": {
                    "properties": {
                        "vector": {
                            "type": "dense_vector",
                            "dims": dimension,
                            "index": True,
                            "similarity": "cosine"
                        },
                        "pdf_id": {
                            "type": "keyword"
                        },
                        "page_num": {
                            "type": "integer"
                        },
                        "patch_index": {
                            "type": "integer"
                        },
                        "title": {
                            "type": "text"
                        }
                    }
                },
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0  # No replicas for local testing
                }
            }

            await self.client.indices.create(index=collection_name, body=index_body)
            print(f"Created Elasticsearch index: {collection_name} with dimension {dimension}")

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
        """Close Elasticsearch connection"""
        if self.client:
            await self.client.close()
            print("Disconnected from Elasticsearch")