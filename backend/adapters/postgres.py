from typing import List, Dict, Any, Optional
import os
import asyncpg
from fastapi import HTTPException
from .base import VectorDatabase


class PostgresAdapter(VectorDatabase):
    def __init__(self):
        self.name = "PostgreSQL with pgvector"
        self.pool = None
        self.host = os.getenv("POSTGRES_HOST", "localhost")
        self.port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.user = os.getenv("POSTGRES_USER", "vectordb")
        self.password = os.getenv("POSTGRES_PASSWORD", "vectordb123")
        self.database = os.getenv("POSTGRES_DB", "knitting_patterns")

    async def connect(self) -> None:
        """Connect to PostgreSQL and create connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                min_size=2,
                max_size=10,
                command_timeout=60
            )

            # Test connection and ensure pgvector extension is available
            async with self.pool.acquire() as conn:
                # Create pgvector extension if it doesn't exist
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

                # Verify connection
                version = await conn.fetchval("SELECT version()")
                print(f"Connected to PostgreSQL: {version}")

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
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()
            print(f"Disconnected from PostgreSQL")