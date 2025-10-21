# Vector Database Experimentation

Experimenting with embeddings and vector databases

Version: 0.10.0 - 21 Oct 2025

## Quick Start

### Switching Between Databases

This project uses Docker Compose profiles to run one database at a time:

```bash
# Run with Postgres (default)
VECTOR_DB_TYPE=postgres docker-compose --profile postgres up --build

# Run with Qdrant
VECTOR_DB_TYPE=qdrant docker-compose --profile qdrant up --build

# Future databases will follow the same pattern:
# VECTOR_DB_TYPE=redis docker-compose --profile redis up --build
```

**What runs with each command:**
- `backend` service (always)
- `frontend` service (always)
- Database service for the selected profile only

**Why profiles?** Running all 7 databases simultaneously would consume too much disk space and memory. Profiles ensure only the database you're testing is active.

### Running the Application
```bash
# Start all services (using default postgres profile)
VECTOR_DB_TYPE=postgres docker-compose --profile postgres up --build

# Frontend will be available at http://localhost:3000
# Backend API at http://localhost:8000
```

### Generating Embeddings Cache

Before testing vector databases, you need to generate embeddings for the training PDFs:

```bash
# Test with 2 PDFs first (recommended)
docker-compose exec backend python ingest_training_data.py --limit 2

# Or test with specific PDFs
docker-compose exec backend python ingest_training_data.py --pdfs "birdseed.pdf,Chex Cowl.pdf"

# Generate embeddings for all 80 training PDFs (~60-80 minutes on CPU)
docker-compose exec backend python ingest_training_data.py

# To abort: Press Ctrl+C (script will resume from where it left off)
```

Embeddings are saved to `./data/embeddings/` and are automatically skipped if already processed.

## Experiment design

This project aims to test out various vector databases with knitting PDFs.

1. Collect samples of knitting pattern PDFs. 50-100 patterns should suffice.
2. Set up a Python project with Docker compose for local databases.
3. Implement an embedding pipeline with ColPali (running locally).
4. Set up a front-end with a text search box and image similarity search.

The setup will be repeated for the following databases: 
- Postgres + pgvector
- Qdrant
- Redis
- Elasticsearch
- Milvus
- Weaviate
- MongoDB

At the end of each experiment, rank them on the following arbitrary success metrics: 
- Practicality: Which database I'd use again.
- Learnings: Unique features/limitations discovered.
- Fun: How enjoyable was the setup/implementation experience.

After I'm done testing all setups, make a document comparing them all and rank them by my personal and
totally arbitrary preference.

## Database Implementations

### Postgres + pgvector

#### Setup and Basic Operations

```bash
# Start the Postgres service
VECTOR_DB_TYPE=postgres docker-compose --profile postgres up -d

# Check logs
docker-compose logs postgres

# Test database connection
curl http://localhost:8000/api/db/test-connection

# Create the vector collection/table
curl -X POST http://localhost:8000/api/db/create-collection

# Verify table structure
docker exec -it vectordatabaseexperimentation-postgres-1 psql -U vectordb -d knitting_patterns -c "\d patterns"
```

#### Data Ingestion

```bash
# Insert a few test PDFs from cache
curl -X POST "http://localhost:8000/api/db/test-insert?num_pdfs=2"

# Check inserted data
docker exec -it vectordatabaseexperimentation-postgres-1 psql -U vectordb -d knitting_patterns -c "SELECT pdf_id, COUNT(*) FROM patterns GROUP BY pdf_id;"

# Full ingestion of all 80 training PDFs
docker-compose exec backend python ingest_all_training.py

# Verify total count (should be 423,741 embeddings)
docker exec -it vectordatabaseexperimentation-postgres-1 psql -U vectordb -d knitting_patterns -c "SELECT COUNT(*) FROM patterns;"
```

#### Search Operations

```bash
# Text search
curl -X POST http://localhost:8000/api/search/text \
  -H "Content-Type: application/json" \
  -d '{"query": "cable knit pattern", "limit": 5}'

# Search for beginner patterns
curl -X POST http://localhost:8000/api/search/text \
  -H "Content-Type: application/json" \
  -d '{"query": "beginner scarf pattern", "limit": 5}'
```

#### Delete Operations

```bash
# Delete a specific PDF (URL-encode spaces as %20)
curl -X DELETE "http://localhost:8000/api/db/delete-pdf/10.1.21_Knot%20Your%20Mamas%20Headband"

# Verify deletion
docker exec -it vectordatabaseexperimentation-postgres-1 psql -U vectordb -d knitting_patterns -c "SELECT pdf_id, COUNT(*) FROM patterns GROUP BY pdf_id;"
```

#### Storage Usage

```bash
# Check Postgres volume size
docker-compose exec postgres du -sh /var/lib/postgresql/data

# Compare to embeddings cache baseline
du -sh ./data/embeddings
```

#### Performance Evaluation

**Full evaluation results**: [POSTGRES_EVALUATION.md](./POSTGRES_EVALUATION.md)

**Quick Summary**:
- **Ingestion**: 1,385 embeddings/sec
- **Query latency**: p50=1,156ms (mostly ColPali embedding generation, <100ms for actual DB search)
- **Concurrency**: 100% success rate, stable throughput under load
- **Memory**: 12.6GB peak (dominated by ColPali model)
- **Storage**: 1.58GB for 423K vectors (6.3x index overhead)

**Ratings**:
- Practicality: ⭐⭐⭐⭐⭐ (5/5) - Would use again
- Learnings: ⭐⭐⭐⭐ (4/5) - SQL + vectors is powerful
- Fun: ⭐⭐⭐⭐ (4/5) - Smooth, familiar experience

### Qdrant

#### Setup and Basic Operations

```bash
# Start the Qdrant service
VECTOR_DB_TYPE=qdrant docker-compose --profile qdrant up -d

# Check logs
docker-compose logs qdrant

# Test database connection
curl http://localhost:8000/api/db/test-connection

# Create the vector collection
curl -X POST http://localhost:8000/api/db/create-collection

# Verify collection (via Qdrant API)
curl http://localhost:6333/collections/patterns

# Or use Qdrant dashboard at http://localhost:6333/dashboard
```

#### Data Ingestion

```bash
# Insert a few test PDFs from cache
curl -X POST "http://localhost:8000/api/db/test-insert?num_pdfs=2"

# Check inserted data (via Qdrant API)
curl -X POST http://localhost:6333/collections/patterns/points/scroll -H "Content-Type: application/json" -d '{"limit": 10}'

# Full ingestion of all 80 training PDFs
docker-compose exec backend python ingest_all_training.py

# Verify total count (should be 423,741 embeddings)
curl http://localhost:6333/collections/patterns | jq '.result.points_count'
```

#### Search Operations

```bash
# Text search
curl -X POST http://localhost:8000/api/search/text \
  -H "Content-Type: application/json" \
  -d '{"query": "cable knit pattern", "limit": 5}'

# Search for scarf patterns
curl -X POST http://localhost:8000/api/search/text \
  -H "Content-Type: application/json" \
  -d '{"query": "scarf", "limit": 5}'
```

#### Delete Operations

```bash
# Delete a specific PDF (URL-encode spaces as %20)
curl -X DELETE "http://localhost:8000/api/db/delete-pdf/10.1.21_Knot%20Your%20Mamas%20Headband"

# Verify deletion (via search)
curl -X POST http://localhost:8000/api/search/text \
  -H "Content-Type: application/json" \
  -d '{"query": "headband", "limit": 5}'
```

#### Storage Usage

```bash
# Check Qdrant volume size
docker-compose exec qdrant du -sh /qdrant/storage

# Compare to embeddings cache baseline
du -sh ./data/embeddings
```

#### Performance Benchmarking

```bash
# Query latency test (p50, p95, p99)
docker-compose exec backend python scripts/benchmark_search.py

# Concurrent load test
docker-compose exec backend python scripts/load_test.py

# Memory monitoring (run in separate terminal during load test)
docker-compose exec backend python scripts/memory_monitor.py
```

#### Performance Evaluation

**Full evaluation results**: [QDRANT_EVALUATION.md](./QDRANT_EVALUATION.md)

**Quick Summary**:
- **Ingestion**: 22,954 embeddings/sec (16.6x faster than Postgres!)
- **Query latency**: p50=1,190ms (mostly ColPali embedding generation, <10ms for actual DB search)
- **Concurrency**: 96% success rate at 10 users (4 failures out of 100)
- **Memory**: 13.0GB peak (dominated by ColPali model)
- **Storage**: 360MB for 423K vectors (1.66x overhead, 4.4x smaller than Postgres!)

**Ratings**:
- Practicality: ⭐⭐⭐⭐⭐ (5/5) - Perfect for vector-first workloads
- Learnings: ⭐⭐⭐⭐⭐ (5/5) - Purpose-built performance is real
- Fun: ⭐⭐⭐⭐⭐ (5/5) - Zero-config magic

### Redis Stack

#### Setup and Basic Operations

```bash
# Start the Redis service
VECTOR_DB_TYPE=redis docker compose --profile redis up -d

# Check logs
docker compose logs redis

# Test database connection
curl http://localhost:8000/api/db/test-connection

# Create the vector index
curl -X POST http://localhost:8000/api/db/create-collection

# Verify index exists (via Redis CLI)
docker compose exec redis redis-cli FT._LIST
```

#### Data Ingestion

```bash
# Insert a few test PDFs from cache
curl -X POST "http://localhost:8000/api/db/test-insert?num_pdfs=2"

# Check inserted data (via Redis CLI)
docker compose exec redis redis-cli DBSIZE

# Full ingestion of all 80 training PDFs
docker compose exec backend python ingest_all_training.py

# Verify total count (should be 423,741 keys)
docker compose exec redis redis-cli DBSIZE
```

#### Search Operations

```bash
# Text search
curl -X POST http://localhost:8000/api/search/text \
  -H "Content-Type: application/json" \
  -d '{"query": "cable knit pattern", "limit": 5}'

# Search for lace patterns
curl -X POST http://localhost:8000/api/search/text \
  -H "Content-Type: application/json" \
  -d '{"query": "lace shawl", "limit": 5}'
```

#### Delete Operations

```bash
# Delete a specific PDF (URL-encode spaces as %20)
curl -X DELETE "http://localhost:8000/api/db/delete-pdf/10.1.21_Knot%20Your%20Mamas%20Headband"

# Verify deletion (via search)
curl -X POST http://localhost:8000/api/search/text \
  -H "Content-Type: application/json" \
  -d '{"query": "headband", "limit": 5}'
```

#### Storage Usage

```bash
# Check Redis memory usage
docker compose exec redis redis-cli INFO memory | grep used_memory_human

# Compare to embeddings cache baseline
du -sh ./data/embeddings
```

#### Performance Evaluation

**Full evaluation results**: [REDIS_EVALUATION.md](./REDIS_EVALUATION.md)

**Quick Summary**:
- **Ingestion**: 5,450 embeddings/sec (3.9x faster than Postgres!)
- **Query latency**: p50=1,165ms (mostly ColPali embedding generation, <100ms for actual DB search)
- **Concurrency**: ⚠️ **55% success rate at 10 users (45% failures!)**
- **Memory**: 13.75GB peak (all data must be in RAM - 1.5GB for vectors)
- **Storage**: 1.45GB RDB snapshot (5.7x overhead)
- **Cold start**: 10-20 seconds to load RDB into memory

**Ratings**:
- Practicality: ⭐⭐ (2/5) - Only as a hot cache layer, not standalone
- Learnings: ⭐⭐⭐⭐ (4/5) - In-memory trade-offs are real
- Fun: ⭐⭐⭐ (3/5) - Fast ingestion, frustrating failures

**Key Insight**: Redis vectors are best used as a **tactical caching layer** on top of a primary vector DB (Postgres/Qdrant), not as a standalone solution. Perfect for caching 10K-100K hot vectors with TTL/LRU eviction.

### Elasticsearch

#### Setup and Basic Operations

```bash
# Start the Elasticsearch service
VECTOR_DB_TYPE=elasticsearch docker compose --profile elasticsearch up -d

# Check logs
docker compose logs elasticsearch

# Test database connection
curl http://localhost:8000/api/db/test-connection

# Create the vector index
curl -X POST http://localhost:8000/api/db/create-collection

# Verify index exists (via Elasticsearch API)
curl http://localhost:9200/patterns
```

#### Data Ingestion

```bash
# Insert a few test PDFs from cache
curl -X POST "http://localhost:8000/api/db/test-insert?num_pdfs=2"

# Check inserted data
curl http://localhost:9200/patterns/_count

# Full ingestion of all 80 training PDFs
docker compose exec backend python ingest_all_training.py

# Verify total count (should be 423,741 embeddings)
curl http://localhost:9200/patterns/_count
```

#### Search Operations

```bash
# Text search
curl -X POST http://localhost:8000/api/search/text \
  -H "Content-Type: application/json" \
  -d '{"query": "cable knit pattern", "limit": 5}'

# Search for scarf patterns
curl -X POST http://localhost:8000/api/search/text \
  -H "Content-Type: application/json" \
  -d '{"query": "scarf", "limit": 5}'
```

#### Delete Operations

```bash
# Delete a specific PDF (URL-encode spaces as %20)
curl -X DELETE "http://localhost:8000/api/db/delete-pdf/10.1.21_Knot%20Your%20Mamas%20Headband"

# Verify deletion (via count)
curl http://localhost:9200/patterns/_count
```

#### Storage Usage

```bash
# Check Elasticsearch volume size
docker compose exec elasticsearch du -sh /usr/share/elasticsearch/data

# Compare to embeddings cache baseline
du -sh ./data/embeddings
```

#### Performance Evaluation

**Full evaluation results**: [ELASTICSEARCH_EVALUATION.md](./ELASTICSEARCH_EVALUATION.md)

**Quick Summary**:
- **Ingestion**: 5,117 embeddings/sec (3.7x faster than Postgres)
- **Query latency**: p50=1,150ms (mostly ColPali embedding generation, <50ms for actual DB search)
- **Concurrency**: 100% success rate at 10 users (perfect reliability!)
- **Memory**: 13.6GB peak (dominated by ColPali model)
- **Storage**: 1.1GB for 423K vectors (5.3x overhead)

**Ratings**:
- Practicality: ⭐⭐⭐⭐ (4/5) - Excellent for hybrid search (vectors + text)
- Learnings: ⭐⭐⭐⭐ (4/5) - Hybrid search capabilities are powerful
- Fun: ⭐⭐⭐⭐ (4/5) - Rock-solid reliability, clean API

**Key Insight**: Elasticsearch excels at **hybrid search** (combining vector similarity with full-text search, filters, and aggregations). Perfect for applications needing both semantic and keyword search in one query.
