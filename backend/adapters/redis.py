from typing import List, Dict, Any, Optional
import os
from fastapi import HTTPException
import redis.asyncio as redis
from .base import VectorDatabase


class RedisAdapter(VectorDatabase):
    def __init__(self):
        self.name = "Redis"
        self.client: Optional[redis.Redis] = None
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", "6379"))

    async def connect(self) -> None:
        """Connect to Redis and verify connection"""
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                decode_responses=False,  # We'll handle binary data for vectors
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Verify connection
            await self.client.ping()
            print(f"Connected to Redis at {self.host}:{self.port}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to connect to Redis: {str(e)}")

    async def create_collection(self, collection_name: str, dimension: int) -> None:
        """Create a Redis index for vector search"""
        if not self.client:
            raise HTTPException(status_code=500, detail="Not connected to Redis")

        try:
            index_name = f"{collection_name}_idx"

            # Drop existing index if it exists (ignore errors if not found)
            try:
                await self.client.execute_command("FT.DROPINDEX", index_name, "DD")
                print(f"Dropped existing index: {index_name}")
            except redis.ResponseError:
                pass  # Index doesn't exist, which is fine

            # Create index with vector field and metadata fields
            # Using HNSW algorithm for vector similarity search
            await self.client.execute_command(
                "FT.CREATE", index_name,
                "ON", "HASH",
                "PREFIX", "1", f"{collection_name}:",
                "SCHEMA",
                "vector", "VECTOR", "HNSW", "6",
                    "TYPE", "FLOAT32",
                    "DIM", str(dimension),
                    "DISTANCE_METRIC", "COSINE",
                "pdf_id", "TAG",
                "page_num", "NUMERIC",
                "patch_index", "NUMERIC",
                "title", "TEXT"
            )

            print(f"Created Redis index: {index_name} with dimension {dimension}")

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
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            print("Disconnected from Redis")