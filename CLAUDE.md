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

### Phase 1: Basic Infrastructure ✅
1. **Hello World Backend** - Minimal FastAPI with single `/` endpoint returning "Hello World", Dockerized ✅
2. **Hello World Frontend** - Minimal React+Vite with "Hello World" text, Dockerized ✅
3. **Connect Frontend to Backend** - Frontend calls backend `/api/health`, display response ✅
4. **Docker Compose Setup** - Both services in one `docker-compose.yml`, verify they communicate ✅

### Phase 2: Core Structure ✅
5. **Add PDF Upload Endpoint** - `/api/upload` that accepts PDF, returns filename (no processing) ✅
6. **Add Frontend Upload** - Basic file input, drag-and-drop for PDFs ✅
7. **Add Database Config** - Environment variable for `VECTOR_DB_TYPE` (postgres/qdrant/etc), endpoint returns current config ✅
8. **Abstract Database Interface** - Create base class with methods returning 501 Not Implemented ✅

### Phase 3: Search Interface (No Real Implementation) ✅
9. **Add Search Endpoints** - `/api/search/text` and `/api/search/image` returning 501 with DB type in error ✅
10. **Add Search UI** - Text input and image upload that show 501 errors nicely ✅
11. **Database Adapter Stubs** - One adapter per database, all returning 501 but with different error messages ✅
12. **Config Switching** - Verify changing `VECTOR_DB_TYPE` switches which 501 error you get ✅

### Phase 4: Ready for Real Implementation ✅
13. **Add Real ColPali Model** - Load actual ColPali model, create embeddings endpoint ✅
14. **PDF Processing** - Convert PDF to images with pdf2image, return page count and image dimensions ✅

#### Phase 4 Implementation Notes
- ColPali v1.3 model (vidore/colpali-v1.3) successfully integrated with automatic download
- Model cached in Docker volume for persistence between container restarts
- **Performance on CPU (Docker on macOS):**
  - PDF embedding generation: ~50-60 seconds per 4-page PDF (1031 patches per page)
  - Query embedding generation: <1 second
  - Model download: ~6GB, one-time on first use
- Docker Desktop memory increased from 8GB to 16GB to handle model loading
- Running on MPS (Apple Silicon GPU) would be ~5-10x faster but requires native execution

### Phase 5: Database Implementation (Repeat for Each Database)

**IMPORTANT**: Work through each step sequentially. Complete and verify each step before proceeding to the next.

#### Phase 5A: Embeddings Preparation (One-time setup)
1. **Create Training/Test Split** - Randomize 93 PDFs, select 80 for training, 13 for testing ✅
   - Created TrainingData.md with randomized split
2. **Build Offline Ingestion Script** - Script to pre-embed training PDFs using ColPali ✅
3. **Generate Embeddings Cache** - Process all 80 training PDFs, save embeddings to `./embeddings/` directory ✅
4. **Verify Cache Format** - Ensure embeddings are loadable and contain expected dimensions ✅

#### Phase 5B: Database Implementation (Repeat for each database)

##### Step 1: Docker Setup ✅
- Add database service to `docker-compose.yml`
- Configure appropriate volumes and network settings
- Start service and verify it's running
- **Verification**: Check docker logs, ensure service is healthy

##### Step 2: Connection Implementation ✅
- Implement `connect()` method in database adapter
- Handle connection pooling if applicable
- Add proper error handling for connection failures
- **Verification**: Test connection with simple ping/health check

##### Step 3: Collection/Table Creation ✅
- Implement `create_collection()` method
- Configure vector dimensions (128 for ColPali)
- Set up appropriate indexes (HNSW with default parameters)
- Define schema for metadata fields
- **Verification**: Check collection exists in database, verify schema

##### Step 4: Insert Implementation ✅
- Implement `insert()` method with batch support
- Load embeddings from cache directory
- Handle metadata (pdf_id, page_num, title, etc.)
- Implement proper error handling and retries
- **Verification**: Insert 2-3 test PDFs, query database directly to verify data

##### Step 5: Search Implementation ✅
- Implement `search()` for text queries
- Support configurable k (top-k results)
- Use cosine similarity as default metric
- Return results with scores and metadata
- **Verification**: Test with known queries, verify result ordering

##### Step 6: Delete Implementation
- Implement `delete()` method
- Support deletion by pdf_id
- Handle cascading deletes for all pages of a PDF
- **Verification**: Delete a test PDF, verify removal from database

##### Step 7: Full Ingestion Test
- Load all 80 training PDFs from cache
- Monitor ingestion time and memory usage
- Verify all documents are searchable
- **Verification**: Count documents in database, test random searches

##### Step 8: Frontend Integration Test
- Test upload of new PDF (from 13 test set)
- Verify real-time embedding generation
- Test search across all ingested content
- Test cross-modal search capabilities
- **Verification**: Complete end-to-end workflow in UI

##### Step 9: Performance Evaluation
- Measure query latency (p50, p95, p99)
- Test with concurrent searches
- Monitor resource usage during operations
- Document any database-specific optimizations applied

##### Step 10: Document Findings
- Record setup complexity and pain points
- Note unique features or limitations discovered
- Rate on practicality, learnings, and fun metrics
- Save performance metrics for comparison

#### Database Order
1. **Postgres + pgvector** (chosen as first implementation)
2. Qdrant
3. Redis
4. Elasticsearch
5. Milvus
6. Weaviate
7. MongoDB

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