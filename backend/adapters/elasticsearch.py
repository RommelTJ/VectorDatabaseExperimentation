from typing import List, Dict, Any, Optional
import os
from fastapi import HTTPException
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
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
        """Insert vectors and metadata into Elasticsearch using bulk API"""
        if not self.client:
            raise HTTPException(status_code=500, detail="Not connected to Elasticsearch")

        if len(vectors) != len(metadata):
            raise HTTPException(status_code=400, detail="Vectors and metadata length mismatch")

        try:
            # Prepare bulk actions
            actions = []
            for i, (vector, meta) in enumerate(zip(vectors, metadata)):
                # Create unique document ID
                pdf_id = meta.get('pdf_id', 'unknown')
                page_num = meta.get('page_num', 0)
                patch_index = meta.get('patch_index', i)

                doc_id = f"{pdf_id}_{page_num}_{patch_index}"

                # Create document with vector and metadata
                action = {
                    "_index": collection_name,
                    "_id": doc_id,
                    "_source": {
                        "vector": vector,
                        "pdf_id": str(pdf_id),
                        "page_num": page_num,
                        "patch_index": patch_index,
                        "title": meta.get('title', '')
                    }
                }
                actions.append(action)

            # Execute bulk insert
            success, failed = await async_bulk(
                self.client,
                actions,
                chunk_size=500,
                raise_on_error=False
            )

            if failed:
                print(f"Warning: {len(failed)} documents failed to insert")

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to insert vectors: {str(e)}")

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors using Elasticsearch kNN search with deduplication"""
        if not self.client:
            raise HTTPException(status_code=500, detail="Not connected to Elasticsearch")

        try:
            # Fetch 3x the requested amount to ensure enough unique PDFs after deduplication
            fetch_size = top_k * 3

            # Build kNN search query
            search_body = {
                "knn": {
                    "field": "vector",
                    "query_vector": query_vector,
                    "k": fetch_size,
                    "num_candidates": fetch_size * 2  # Number of candidates to consider
                },
                "_source": ["pdf_id", "page_num", "patch_index", "title"],
                "size": fetch_size
            }

            # Execute search
            response = await self.client.search(
                index=collection_name,
                body=search_body
            )

            # Parse results and deduplicate by pdf_id
            seen_pdfs = {}
            for hit in response['hits']['hits']:
                source = hit['_source']
                pdf_id = source['pdf_id']
                score = hit['_score']

                # Keep only the first (highest scoring) result for each pdf_id
                if pdf_id not in seen_pdfs:
                    seen_pdfs[pdf_id] = {
                        'pdf_id': pdf_id,
                        'page_num': source['page_num'],
                        'patch_index': source['patch_index'],
                        'title': source['title'],
                        'score': score
                    }

            # Convert to list and take top_k
            results = list(seen_pdfs.values())[:top_k]

            return results

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to search: {str(e)}")

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