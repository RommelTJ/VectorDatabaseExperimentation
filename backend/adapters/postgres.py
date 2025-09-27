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
        """Create a table for storing vectors with metadata"""
        if not self.pool:
            await self.connect()

        try:
            async with self.pool.acquire() as conn:
                # Drop table if exists (for experimentation)
                await conn.execute(f"DROP TABLE IF EXISTS {collection_name} CASCADE")

                # Create table with vector column and metadata
                create_table_query = f"""
                    CREATE TABLE {collection_name} (
                        id SERIAL PRIMARY KEY,
                        pdf_id VARCHAR(255) NOT NULL,
                        page_num INTEGER NOT NULL,
                        patch_index INTEGER NOT NULL,
                        embedding vector({dimension}) NOT NULL,
                        title TEXT,
                        difficulty VARCHAR(50),
                        yarn_weight VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(pdf_id, page_num, patch_index)
                    )
                """
                await conn.execute(create_table_query)

                # Create HNSW index for cosine similarity
                create_index_query = f"""
                    CREATE INDEX ON {collection_name}
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64)
                """
                await conn.execute(create_index_query)

                # Create index on pdf_id for faster lookups/deletes
                await conn.execute(f"CREATE INDEX ON {collection_name} (pdf_id)")

                print(f"Created collection '{collection_name}' with dimension {dimension}")

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
        if not self.pool:
            await self.connect()

        if len(vectors) != len(metadata):
            raise HTTPException(
                status_code=400,
                detail="Number of vectors must match number of metadata entries"
            )

        try:
            async with self.pool.acquire() as conn:
                # Prepare batch insert data
                insert_data = []
                for i, (vector, meta) in enumerate(zip(vectors, metadata)):
                    # Convert vector to string format for pgvector
                    vector_str = '[' + ','.join(str(x) for x in vector) + ']'
                    insert_data.append((
                        meta.get('pdf_id', ''),
                        meta.get('page_num', 0),
                        meta.get('patch_index', i),
                        vector_str,  # pgvector expects string format
                        meta.get('title', None),
                        meta.get('difficulty', None),
                        meta.get('yarn_weight', None)
                    ))

                # Batch insert with explicit casting
                insert_query = f"""
                    INSERT INTO {collection_name}
                    (pdf_id, page_num, patch_index, embedding, title, difficulty, yarn_weight)
                    VALUES ($1, $2, $3, $4::vector, $5, $6, $7)
                    ON CONFLICT (pdf_id, page_num, patch_index)
                    DO UPDATE SET
                        embedding = EXCLUDED.embedding,
                        title = EXCLUDED.title,
                        difficulty = EXCLUDED.difficulty,
                        yarn_weight = EXCLUDED.yarn_weight,
                        created_at = CURRENT_TIMESTAMP
                """

                # Execute batch insert
                await conn.executemany(insert_query, insert_data)

                print(f"Inserted {len(vectors)} vectors into '{collection_name}'")

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