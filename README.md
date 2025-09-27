# Vector Database Experimentation

Experimenting with embeddings and vector databases

Version: 0.1.0 - 20 Sep 2025

## Quick Start

### Running the Application
```bash
# Start all services
docker-compose up

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
docker-compose up -d postgres

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

#### Performance Results

- **Full Ingestion**: 423,741 embeddings in 305.91 seconds
- **Average Speed**: 1,385 embeddings/second
- **Average per PDF**: 3.82 seconds
- **Search Latency**: < 100ms for top-5 results
