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
        """Create a collection with vector search index"""
        if not self.client:
            await self.connect()

        try:
            # Drop collection if exists (for experimentation)
            await self.db[collection_name].drop()

            # Create collection explicitly (optional, but good for clarity)
            await self.db.create_collection(collection_name)

            # Create vector search index using MongoDB command
            # MongoDB Atlas Local uses createSearchIndexes command
            collection = self.db[collection_name]

            create_index_command = {
                "createSearchIndexes": collection_name,
                "indexes": [
                    {
                        "name": "vector_index",
                        "type": "vectorSearch",
                        "definition": {
                            "fields": [
                                {
                                    "type": "vector",
                                    "path": "embedding",
                                    "numDimensions": dimension,
                                    "similarity": "cosine"
                                }
                            ]
                        }
                    }
                ]
            }

            result = await self.db.command(create_index_command)
            print(f"Vector search index creation result: {result}")

            # Create regular index on pdf_id for faster lookups/deletes
            await collection.create_index("pdf_id")

            print(f"Created collection '{collection_name}' with dimension {dimension} and vector search index")

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
        """Insert vectors with metadata into the collection"""
        if not self.client:
            await self.connect()

        if len(vectors) != len(metadata):
            raise HTTPException(
                status_code=400,
                detail="Number of vectors must match number of metadata entries"
            )

        try:
            collection = self.db[collection_name]

            # Prepare documents for batch insert
            documents = []
            for i, (vector, meta) in enumerate(zip(vectors, metadata)):
                doc = {
                    "pdf_id": meta.get('pdf_id', ''),
                    "page_num": meta.get('page_num', 0),
                    "patch_index": meta.get('patch_index', i),
                    "embedding": vector,  # MongoDB stores arrays natively
                    "title": meta.get('title', None)
                }
                documents.append(doc)

            # Batch insert with ordered=False for better performance
            # This allows MongoDB to continue inserting even if some documents fail
            if documents:
                result = await collection.insert_many(documents, ordered=False)
                print(f"Inserted {len(result.inserted_ids)} vectors into '{collection_name}'")

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"{self.name}: Failed to insert - {str(e)}"
            )

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors using MongoDB vector search"""
        if not self.client:
            await self.connect()

        try:
            collection = self.db[collection_name]

            # MongoDB vector search aggregation pipeline
            # Fetch 3x results to ensure enough unique documents after deduplication
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index",
                        "path": "embedding",
                        "queryVector": query_vector,
                        "numCandidates": top_k * 10,  # Number of candidates to consider
                        "limit": top_k * 3  # Fetch 3x results for deduplication
                    }
                },
                {
                    "$addFields": {
                        "score": {"$meta": "vectorSearchScore"}
                    }
                },
                # Deduplicate by pdf_id, keeping the best scoring patch per document
                {
                    "$sort": {"score": -1}
                },
                {
                    "$group": {
                        "_id": "$pdf_id",
                        "pdf_id": {"$first": "$pdf_id"},
                        "page_num": {"$first": "$page_num"},
                        "patch_index": {"$first": "$patch_index"},
                        "title": {"$first": "$title"},
                        "score": {"$first": "$score"}
                    }
                },
                {
                    "$sort": {"score": -1}
                },
                {
                    "$limit": top_k
                },
                # Project to remove the _id field used for grouping
                {
                    "$project": {
                        "_id": 0,
                        "pdf_id": 1,
                        "page_num": 1,
                        "patch_index": 1,
                        "title": 1,
                        "score": 1
                    }
                }
            ]

            # Execute aggregation pipeline
            cursor = collection.aggregate(pipeline)
            results = await cursor.to_list(length=top_k)

            return results

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"{self.name}: Failed to search - {str(e)}"
            )

    async def delete(
        self,
        collection_name: str,
        ids: List[str]
    ) -> None:
        """Delete vectors by pdf_id (cascading delete for all pages)"""
        if not self.client:
            await self.connect()

        try:
            collection = self.db[collection_name]

            # Delete all documents matching the pdf_ids
            result = await collection.delete_many({"pdf_id": {"$in": ids}})

            print(f"Deleted {result.deleted_count} vectors for {len(ids)} PDFs from '{collection_name}'")

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"{self.name}: Failed to delete vectors - {str(e)}"
            )

    async def disconnect(self) -> None:
        """Close the MongoDB connection"""
        if self.client:
            self.client.close()
            print(f"Disconnected from MongoDB")