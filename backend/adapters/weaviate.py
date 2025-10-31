from typing import List, Dict, Any, Optional
import os
import uuid
import weaviate
from weaviate.classes.config import Configure, Property, DataType, VectorDistances
from weaviate.classes.query import MetadataQuery, Filter
from weaviate.util import generate_uuid5
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
        """Create a Weaviate collection (class) for storing vectors with metadata"""
        if not self.client:
            await self.connect()

        try:
            # Capitalize collection name (Weaviate convention for class names)
            class_name = collection_name.capitalize()

            # Delete collection if exists (for experimentation)
            if self.client.collections.exists(class_name):
                self.client.collections.delete(class_name)
                print(f"Deleted existing collection: {class_name}")

            # Create collection with properties and vector configuration
            self.client.collections.create(
                name=class_name,
                properties=[
                    Property(name="pdf_id", data_type=DataType.TEXT),
                    Property(name="page_num", data_type=DataType.INT),
                    Property(name="patch_index", data_type=DataType.INT),
                    Property(name="title", data_type=DataType.TEXT),
                ],
                vectorizer_config=Configure.Vectorizer.none(),  # We provide our own vectors
                vector_index_config=Configure.VectorIndex.hnsw(
                    distance_metric=VectorDistances.COSINE
                )
            )

            print(f"Created Weaviate collection '{class_name}' with dimension {dimension}")

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
        """Insert vectors with metadata into the Weaviate collection"""
        if not self.client:
            await self.connect()

        if len(vectors) != len(metadata):
            raise HTTPException(
                status_code=400,
                detail="Number of vectors must match number of metadata entries"
            )

        try:
            # Capitalize collection name to match Weaviate class name
            class_name = collection_name.capitalize()
            collection = self.client.collections.get(class_name)

            # Prepare data objects for batch insert
            objects = []
            for i, (vector, meta) in enumerate(zip(vectors, metadata)):
                # Generate deterministic UUID from metadata (for idempotent inserts)
                pdf_id = meta.get('pdf_id', '')
                page_num = meta.get('page_num', 0)
                patch_index = meta.get('patch_index', i)

                # Create deterministic UUID using pdf_id, page_num, and patch_index
                unique_str = f"{pdf_id}_{page_num}_{patch_index}"
                object_uuid = generate_uuid5(unique_str)

                # Create data object with properties and vector
                obj = {
                    "uuid": object_uuid,
                    "properties": {
                        "pdf_id": str(pdf_id),
                        "page_num": int(page_num),
                        "patch_index": int(patch_index),
                        "title": meta.get('title', '')
                    },
                    "vector": vector
                }
                objects.append(obj)

            # Batch insert objects
            with collection.batch.dynamic() as batch:
                for obj in objects:
                    batch.add_object(
                        properties=obj["properties"],
                        vector=obj["vector"],
                        uuid=obj["uuid"]
                    )

            print(f"Inserted {len(objects)} vectors into '{class_name}'")

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"{self.name}: Failed to insert vectors - {str(e)}"
            )

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors using cosine similarity with deduplication"""
        if not self.client:
            await self.connect()

        try:
            # Capitalize collection name to match Weaviate class name
            class_name = collection_name.capitalize()
            collection = self.client.collections.get(class_name)

            # Search for top candidates (3x to ensure enough unique documents)
            response = collection.query.near_vector(
                near_vector=query_vector,
                limit=top_k * 3,
                return_metadata=MetadataQuery(distance=True)
            )

            # Deduplicate by pdf_id - keep best scoring patch per document
            seen_pdfs = {}
            for obj in response.objects:
                pdf_id = obj.properties.get('pdf_id')

                # Convert distance to similarity score (for cosine: similarity = 1 - distance)
                distance = obj.metadata.distance if obj.metadata.distance is not None else 1.0
                score = 1.0 - distance

                # Keep the first (highest scoring) result for each pdf_id
                if pdf_id and pdf_id not in seen_pdfs:
                    seen_pdfs[pdf_id] = {
                        'pdf_id': pdf_id,
                        'page_num': obj.properties.get('page_num'),
                        'patch_index': obj.properties.get('patch_index'),
                        'title': obj.properties.get('title'),
                        'score': score
                    }

            # Convert to list and take top_k
            results = list(seen_pdfs.values())[:top_k]

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
            # Capitalize collection name to match Weaviate class name
            class_name = collection_name.capitalize()
            collection = self.client.collections.get(class_name)

            # Delete all objects matching any of the pdf_ids
            for pdf_id in ids:
                collection.data.delete_many(
                    where=Filter.by_property("pdf_id").equal(pdf_id)
                )
                print(f"Deleted objects for pdf_id: {pdf_id}")

            print(f"Deleted vectors for {len(ids)} PDFs from '{class_name}'")

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"{self.name}: Failed to delete vectors - {str(e)}"
            )

    async def disconnect(self) -> None:
        """Close the connection to Weaviate"""
        if self.client:
            self.client.close()
            print(f"Disconnected from Weaviate")