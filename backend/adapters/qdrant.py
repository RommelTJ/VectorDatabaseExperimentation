from typing import List, Dict, Any, Optional
import os
import hashlib
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchAny
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

            # Test connection by getting collections (returns empty list if none exist)
            collections = self.client.get_collections()
            print(f"Connected to Qdrant: {len(collections.collections)} collections found")

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

    def _generate_point_id(self, pdf_id: str, page_num: int, patch_index: int) -> str:
        """Generate a deterministic unique ID for a point"""
        # Create a unique string from metadata
        unique_str = f"{pdf_id}_{page_num}_{patch_index}"
        # Hash it to get a consistent ID
        hash_obj = hashlib.sha256(unique_str.encode())
        # Convert to integer (Qdrant supports int or UUID)
        return int(hash_obj.hexdigest()[:16], 16)

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
            # Create points for batch upsert
            points = []
            for i, (vector, meta) in enumerate(zip(vectors, metadata)):
                # Generate deterministic ID from metadata
                point_id = self._generate_point_id(
                    meta.get('pdf_id', ''),
                    meta.get('page_num', 0),
                    meta.get('patch_index', i)
                )

                # Create point with vector and payload (metadata)
                point = PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        'pdf_id': meta.get('pdf_id', ''),
                        'page_num': meta.get('page_num', 0),
                        'patch_index': meta.get('patch_index', i),
                        'title': meta.get('title', None)
                    }
                )
                points.append(point)

            # Batch upsert points (insert or update if exists)
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )

            print(f"Inserted {len(points)} vectors into '{collection_name}'")

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
        """Search for similar vectors using cosine similarity"""
        if not self.client:
            await self.connect()

        try:
            # Search for top candidates (3x to ensure enough unique documents)
            search_results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=top_k * 3
            )

            # Deduplicate by pdf_id - keep best scoring patch per document
            seen_pdfs = {}
            for result in search_results:
                pdf_id = result.payload.get('pdf_id')

                # Keep the first (highest scoring) result for each pdf_id
                if pdf_id not in seen_pdfs:
                    seen_pdfs[pdf_id] = {
                        'pdf_id': pdf_id,
                        'page_num': result.payload.get('page_num'),
                        'patch_index': result.payload.get('patch_index'),
                        'title': result.payload.get('title'),
                        'score': result.score
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
            # Delete all points matching any of the pdf_ids
            # Using MatchAny to match multiple pdf_ids
            self.client.delete(
                collection_name=collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="pdf_id",
                            match=MatchAny(any=ids)
                        )
                    ]
                )
            )

            print(f"Deleted vectors for {len(ids)} PDFs from '{collection_name}'")

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"{self.name}: Failed to delete vectors - {str(e)}"
            )

    async def disconnect(self) -> None:
        """Close the connection"""
        if self.client:
            self.client.close()
            print(f"Disconnected from Qdrant")