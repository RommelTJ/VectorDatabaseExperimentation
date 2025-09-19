# Vector Database Experimentation

Experimenting with embeddings and vector databases

Version: 0.0.3 - 13 Sep 2025

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
