# Vector Database Experimentation - Design Notes

## Project Overview
Testing various vector databases with knitting pattern PDFs using ColPali multimodal embeddings. The goal is to compare database performance and developer experience across multiple platforms.

## Databases to Test
- Postgres + pgvector
- Qdrant
- Redis
- Elasticsearch
- Milvus
- Weaviate
- MongoDB

## Key Design Considerations

### Content Processing
Knitting patterns contain both text (instructions, materials) and visual elements (charts, diagrams, photos). The system needs to handle:
- PDF pages as images (no text extraction needed)
- Patch-based embeddings that capture text, charts, and images together
- Multimodal embeddings via ColPali (running locally)

### Search Capabilities
Three search modalities are being considered:
- **Text-to-text**: Search instructions by description
- **Image-to-image**: Find similar stitch patterns visually
- **Cross-modal**: Find patterns by describing what you want

## Generic Interface Approach

### Core Abstract Components
- `VectorDatabase`: Abstract base for database operations
- `PDFProcessor`: Handles content extraction and embedding
- `KnittingPatternSearch`: Main interface combining processing and search

### Key Operations
- `connect()`: Database connection
- `create_collection()`: Initialize storage
- `insert()`: Add embedded content
- `search()`: Query with text/image/hybrid
- `delete()`: Remove content

Note: Update operations intentionally omitted since PDFs are treated as immutable artifacts in this experiment.

## Database Patterns Observed

### Common Across All Databases
- HNSW indexing as dominant algorithm
- Support for cosine similarity, dot product, Euclidean distance
- Batch operations for performance
- Configurable top-k results

### Key Differences
- **Schema flexibility**: Ranges from strict (Milvus, Weaviate) to flexible (Redis, MongoDB)
- **Query languages**: SQL (Postgres), JSON (Elasticsearch), GraphQL-like (Weaviate)
- **Storage models**: Collections, tables, documents, or hash-based
- **Unique features**: Each database offers specialized capabilities that may influence implementation

## Implementation Notes

### Content Storage Strategy
Each PDF generates:
- Multiple page embeddings (one per PDF page)
- Patch-based embeddings from ColPali (capturing text and visual elements)
- Metadata (title, difficulty, yarn weight, etc.)

### Search Implementation
The generic interface should support:
- Single modality search (text-only or image-only)
- Hybrid search combining multiple modalities
- Metadata filtering alongside vector similarity

## Next Steps
1. Start with one database for initial implementation
2. Build PDF processing pipeline treating pages as images
3. Integrate ColPali for local multimodal embeddings
4. Create database adapters following the generic interface
5. Build simple frontend for testing search capabilities

## Success Metrics for Evaluation
- **Practicality**: Ease of future use
- **Learnings**: Unique features/limitations discovered
- **Fun**: Developer experience during implementation