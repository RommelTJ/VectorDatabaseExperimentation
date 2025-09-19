from .base import VectorDatabase
from .postgres import PostgresAdapter
from .qdrant import QdrantAdapter
from .redis import RedisAdapter
from .elasticsearch import ElasticsearchAdapter
from .milvus import MilvusAdapter
from .weaviate import WeaviateAdapter
from .mongodb import MongoDBAdapter


def get_database_adapter(db_type: str) -> VectorDatabase:
    adapters = {
        'postgres': PostgresAdapter,
        'qdrant': QdrantAdapter,
        'redis': RedisAdapter,
        'elasticsearch': ElasticsearchAdapter,
        'milvus': MilvusAdapter,
        'weaviate': WeaviateAdapter,
        'mongodb': MongoDBAdapter
    }

    adapter_class = adapters.get(db_type.lower())
    if not adapter_class:
        raise ValueError(f"Unsupported database type: {db_type}")

    return adapter_class()


__all__ = [
    'VectorDatabase',
    'PostgresAdapter',
    'QdrantAdapter',
    'RedisAdapter',
    'ElasticsearchAdapter',
    'MilvusAdapter',
    'WeaviateAdapter',
    'MongoDBAdapter',
    'get_database_adapter'
]