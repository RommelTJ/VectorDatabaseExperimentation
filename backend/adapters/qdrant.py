from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from .base import VectorDatabase


class QdrantAdapter(VectorDatabase):
    def __init__(self):
        self.name = "Qdrant"

    async def connect(self) -> None:
        raise HTTPException(status_code=501, detail=f"{self.name}: connect not implemented")

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
        raise HTTPException(status_code=501, detail=f"{self.name}: disconnect not implemented")