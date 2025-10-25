from typing import List, Dict, Any, Optional
import os
import hashlib
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
        """Insert vectors and metadata into Milvus using batch insert"""
        if not self.client:
            raise HTTPException(status_code=500, detail="Not connected to Milvus")

        if len(vectors) != len(metadata):
            raise HTTPException(status_code=400, detail="Vectors and metadata length mismatch")

        try:
            # Prepare data for insertion
            # MilvusClient expects a list of dictionaries
            # Note: The 'id' field must be an int64 (auto_id is False in the schema)
            # We hash the compound key to get a deterministic integer ID
            data = []
            for i, (vector, meta) in enumerate(zip(vectors, metadata)):
                pdf_id = meta.get('pdf_id', 'unknown')
                page_num = meta.get('page_num', 0)
                patch_index = meta.get('patch_index', i)

                # Create deterministic integer ID by hashing the compound key
                # This ensures same PDF/page/patch always gets same ID (upsert behavior)
                compound_key = f"{pdf_id}_{page_num}_{patch_index}"
                hash_int = int(hashlib.md5(compound_key.encode()).hexdigest()[:16], 16)
                # Convert to signed int64 range
                int64_id = hash_int % (2**63)

                # Create document with integer id, vector, and metadata
                # Dynamic fields (pdf_id, page_num, etc.) are supported
                doc = {
                    "id": int64_id,
                    "vector": vector,
                    "pdf_id": str(pdf_id),
                    "page_num": page_num,
                    "patch_index": patch_index,
                    "title": meta.get('title', '')
                }
                data.append(doc)

            # Insert data in batches of 500
            batch_size = 500
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                self.client.insert(
                    collection_name=collection_name,
                    data=batch
                )

            print(f"Inserted {len(data)} vectors into {collection_name}")

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to insert vectors: {str(e)}")

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors using Milvus vector search with deduplication"""
        if not self.client:
            raise HTTPException(status_code=500, detail="Not connected to Milvus")

        try:
            # Fetch 3x the requested amount to ensure enough unique PDFs after deduplication
            fetch_size = top_k * 3

            # Execute vector search
            # MilvusClient.search returns results with distance scores
            results = self.client.search(
                collection_name=collection_name,
                data=[query_vector],  # Must be a list of vectors
                limit=fetch_size,
                output_fields=["pdf_id", "page_num", "patch_index", "title"]
            )

            # Parse results and deduplicate by pdf_id
            # Results is a list of lists (one list per query vector)
            seen_pdfs = {}
            if results and len(results) > 0:
                for hit in results[0]:  # Get first query's results
                    pdf_id = hit.get('entity', {}).get('pdf_id') or hit.get('pdf_id')

                    # Milvus returns distance (lower is better for COSINE)
                    # Convert to similarity score (higher is better)
                    distance = hit.get('distance', 0.0)
                    score = 1.0 - distance  # For cosine, distance is 1 - similarity

                    # Keep only the first (highest scoring) result for each pdf_id
                    if pdf_id and pdf_id not in seen_pdfs:
                        entity = hit.get('entity', {})
                        seen_pdfs[pdf_id] = {
                            'pdf_id': pdf_id,
                            'page_num': entity.get('page_num', hit.get('page_num', 0)),
                            'patch_index': entity.get('patch_index', hit.get('patch_index', 0)),
                            'title': entity.get('title', hit.get('title', '')),
                            'score': score
                        }

            # Convert to list and take top_k
            final_results = list(seen_pdfs.values())[:top_k]

            return final_results

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to search: {str(e)}")

    async def delete(
        self,
        collection_name: str,
        ids: List[str]
    ) -> None:
        """Delete vectors by pdf_id using expression-based deletion"""
        if not self.client:
            raise HTTPException(status_code=500, detail="Not connected to Milvus")

        try:
            for pdf_id in ids:
                # Delete all entities matching this pdf_id using filter expression
                # Milvus uses filter expressions like: pdf_id == "value"
                filter_expr = f'pdf_id == "{pdf_id}"'

                self.client.delete(
                    collection_name=collection_name,
                    filter=filter_expr
                )

                print(f"Deleted entities for pdf_id: {pdf_id}")

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete: {str(e)}")

    async def disconnect(self) -> None:
        """Disconnect from Milvus"""
        try:
            if self.client:
                self.client.close()
                self.client = None
                print(f"Disconnected from Milvus")
        except Exception as e:
            print(f"Error disconnecting from Milvus: {str(e)}")