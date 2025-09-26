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
