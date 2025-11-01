from typing import List, Dict, Any, Optional
import os
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import HTTPException
from .base import VectorDatabase


class MongoDBAdapter(VectorDatabase):
    def __init__(self):
        self.name = "MongoDB"
        self.client = None
        self.db = None
        self.host = os.getenv("MONGODB_HOST", "localhost")
        self.port = int(os.getenv("MONGODB_PORT", "27017"))
        self.user = os.getenv("MONGODB_USER", "vectordb")
        self.password = os.getenv("MONGODB_PASSWORD", "vectordb123")
        self.database = os.getenv("MONGODB_DB", "knitting_patterns")

    async def connect(self) -> None:
        """Connect to MongoDB using motor async driver"""
        try:
            # Build connection string
            connection_string = f"mongodb://{self.user}:{self.password}@{self.host}:{self.port}/?authSource=admin"

            # Create async MongoDB client
            self.client = AsyncIOMotorClient(
                connection_string,
                serverSelectionTimeoutMS=5000,
                maxPoolSize=10,
                minPoolSize=2
            )

            # Get database reference
            self.db = self.client[self.database]

            # Test connection by pinging the server
            await self.client.admin.command('ping')

            # Get server info
            server_info = await self.client.server_info()
            print(f"Connected to MongoDB: version {server_info.get('version', 'unknown')}")

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
        """Close the MongoDB connection"""
        if self.client:
            self.client.close()
            print(f"Disconnected from MongoDB")