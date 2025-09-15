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

## Tech Stack

### Backend (Python)
- **FastAPI**: Async API framework for handling requests
- **ColPali v1.3**: Local multimodal embeddings (treats PDF pages as images)
- **pdf2image**: Simple PDF to image conversion
- **Pydantic**: Data validation and settings management
- **Python 3.11+**: Modern Python features and performance

### Frontend
- **React with TypeScript**: UI framework
- **Vite**: Fast build tool and dev server
- **Tailwind CSS**: Utility-first styling (no component libraries)
- **Basic React state**: Simple state management (no Redux/Zustand)

### Infrastructure
- **Docker Compose**: Orchestrate all vector databases locally
- **REST API**: Simple HTTP communication (no WebSockets)
- **Local file uploads**: Direct to API (no cloud storage or pre-signed URLs)

### Development Approach
- **No tests**: Focus on experimentation
- **No linting/formatting**: Keep it simple
- **No CI/CD**: Local development only
- **No production concerns**: Laptop-only deployment

## Implementation Plan

### Phase 1: Basic Infrastructure
1. **Hello World Backend** - Minimal FastAPI with single `/` endpoint returning "Hello World", Dockerized
2. **Hello World Frontend** - Minimal React+Vite with "Hello World" text, Dockerized
3. **Connect Frontend to Backend** - Frontend calls backend `/api/health`, display response
4. **Docker Compose Setup** - Both services in one `docker-compose.yml`, verify they communicate

### Phase 2: Core Structure
5. **Add PDF Upload Endpoint** - `/api/upload` that accepts PDF, returns filename (no processing)
6. **Add Frontend Upload** - Basic file input, drag-and-drop for PDFs
7. **Add Database Config** - Environment variable for `VECTOR_DB_TYPE` (postgres/qdrant/etc), endpoint returns current config
8. **Abstract Database Interface** - Create base class with methods returning 501 Not Implemented

### Phase 3: Search Interface (No Real Implementation)
9. **Add Search Endpoints** - `/api/search/text` and `/api/search/image` returning 501 with DB type in error
10. **Add Search UI** - Text input and image upload that show 501 errors nicely
11. **Database Adapter Stubs** - One adapter per database, all returning 501 but with different error messages
12. **Config Switching** - Verify changing `VECTOR_DB_TYPE` switches which 501 error you get

### Phase 4: Ready for Real Implementation
13. **Add Real ColPali Model** - Load actual ColPali model, create embeddings endpoint
14. **PDF Processing** - Convert PDF to images with pdf2image, return page count and image dimensions

### Phase 5: First Database Implementation
15. **Choose first database** (likely Postgres+pgvector or Qdrant)
16. **Implement real operations** - Connect, create collection, insert, search, delete
17. **Wire up ColPali** - Generate real embeddings and store them
18. **Test end-to-end** - Upload PDF, process, search

### Implementation Notes
- Each step should be minimal and verifiable via Docker
- User will check each step before proceeding to next
- All database adapters initially return HTTP 501 Not Implemented
- Configuration via environment variables to switch between databases
- No tests, linting, or production concerns

## Success Metrics for Evaluation
- **Practicality**: Ease of future use
- **Learnings**: Unique features/limitations discovered
- **Fun**: Developer experience during implementation