# Vector Database Showdown: Overall Findings

**Project**: Testing 7 vector databases with 423,741 ColPali embeddings (128d) from 80 knitting pattern PDFs
**Hardware**: Docker Desktop on macOS (16GB RAM, CPU-only)
**Date**: September 30 - November 2, 2025

---

## Executive Summary

After testing all 7 databases, my personal rankings are:

1. **Qdrant** - Best all-around balance of speed, storage efficiency, and developer experience
2. **Weaviate** - Best for production read-heavy workloads requiring maximum reliability
3. **Postgres + pgvector** - Most practical for teams already using Postgres (one database for everything!)
4. **Elasticsearch** - Best for hybrid search (different use case: vectors + full-text + aggregations)
5. **Milvus** - Feature-rich powerhouse (GPU support, disk indices, multiple index types) - production-ready for experts

The specialized tools (not for standalone vector search):

6. **Redis** - Tactical caching layer only (45% failure rate at 10 users)
7. **MongoDB** - Write buffer only (6.5x latency degradation under load)

---

## Performance Comparison

### Ingestion Speed (embeddings/second)

| Rank | Database          | Speed  | Notes                                |
|------|-------------------|--------|--------------------------------------|
| 1    | **MongoDB**       | 38,596 | 🏆 Fastest, but terrible concurrency |
| 2    | **Milvus**        | 32,496 | 🥈 Fast, but 90% success rate        |
| 3    | **Qdrant**        | 22,954 | 🥉 Balanced speed + reliability      |
| 4    | **Redis**         | 5,450  | Fast, but 55% success rate           |
| 5    | **Elasticsearch** | 5,117  | Solid reliability                    |
| 6    | **Postgres**      | 1,385  | Slower, but 100% reliable            |
| 7    | **Weaviate**      | 811    | Slowest, trades writes for reads     |

**Key Insight**: MongoDB and Milvus are write specialists. Their speed comes at the cost of reliability under load.

### Query Latency (p50, single user)

| Rank | Database          | Latency | Actual DB Time |
|------|-------------------|---------|----------------|
| 1    | **Weaviate**      | 560ms   | <10ms          |
| 2    | **Milvus**        | 700ms   | <10ms          |
| 3    | **MongoDB**       | 761ms   | ~100ms         |
| 4    | **Elasticsearch** | 1,150ms | <50ms          |
| 5    | **Postgres**      | 1,156ms | <100ms         |
| 6    | **Redis**         | 1,165ms | <100ms         |
| 7    | **Qdrant**        | 1,190ms | <10ms          |

**Note**: Most latency (~1,100ms) is ColPali embedding generation. Actual vector search is <100ms for all databases. Weaviate's 2x advantage shows HNSW optimization paying off.

### Concurrency (10 concurrent users)

| Rank | Database          | Success Rate | p50 Latency | Notes                |
|------|-------------------|--------------|-------------|----------------------|
| 1    | **Elasticsearch** | 100%         | 11,163ms    | Rock solid           |
| 1    | **Postgres**      | 100%         | 11,349ms    | Rock solid           |
| 1    | **Weaviate**      | 100%         | 5,292ms     | Rock solid + fastest |
| 1    | **MongoDB**       | 100%         | 19,572ms    | 🚨 6.5x degradation! |
| 5    | **Qdrant**        | 96%          | 10,552ms    | 4 failures           |
| 6    | **Milvus**        | 90%          | 13,692ms    | 10 failures          |
| 7    | **Redis**         | 55%          | 11,622ms    | 🚨 45% failures!     |

**Key Insight**: Success rate matters more than raw speed. MongoDB's 100% is misleading - 6.5x latency increase is catastrophic.

### Storage Efficiency (overhead multiplier)

| Rank | Database          | Storage | Overhead | Notes             |
|------|-------------------|---------|----------|-------------------|
| 1    | **Qdrant**        | 360 MB  | 1.66x    | 🏆 Most efficient |
| 2    | **Weaviate**      | 641 MB  | 3.1x     | Excellent         |
| 3    | **Elasticsearch** | 1.1 GB  | 5.3x     | Good              |
| 4    | **Redis**         | 1.45 GB | 5.7x     | Acceptable        |
| 5    | **Postgres**      | 1.58 GB | 6.3x     | Acceptable        |
| 6    | **MongoDB**       | 2.5 GB  | 12.1x    | 🚨 Worst          |

**Baseline**: 207 MB raw embeddings
**Key Insight**: Qdrant's 1.66x vs MongoDB's 12.1x is a 7.3x difference. At scale, this translates to massive cost savings.

---

## Overall Ratings

### My Personal Rankings (Totally Arbitrary)

**Final Ranking by Combined Score:**

| Rank | Database          | Practicality | Learnings | Fun   | Total | Notes                        |
|------|-------------------|--------------|-----------|-------|-------|------------------------------|
| 1    | **Qdrant**        | ⭐⭐⭐⭐⭐        | ⭐⭐⭐⭐⭐     | ⭐⭐⭐⭐⭐ | 15/15 | 🏆 Perfect all-rounder       |
| 2    | **Weaviate**      | ⭐⭐⭐⭐         | ⭐⭐⭐⭐⭐     | ⭐⭐⭐   | 12/15 | 🥈 Production champion       |
| 3    | **Postgres**      | ⭐⭐⭐⭐⭐        | ⭐⭐⭐⭐      | ⭐⭐⭐⭐  | 13/15 | 🥉 One DB for everything     |
| 4    | **Elasticsearch** | ⭐⭐⭐⭐         | ⭐⭐⭐⭐      | ⭐⭐⭐⭐  | 12/15 | Hybrid search specialist     |
| 5    | **Milvus**        | ⭐⭐⭐          | ⭐⭐⭐⭐      | ⭐⭐    | 9/15  | Feature-rich but complex     |
| 6    | **Redis**         | ⭐⭐           | ⭐⭐⭐⭐      | ⭐⭐⭐   | 9/15  | Cache layer only             |
| 7    | **MongoDB**       | ⭐⭐           | ⭐⭐⭐⭐⭐     | ⭐⭐    | 9/15  | Write buffer only            |

---

## Detailed Analysis

### 🏆 #1: Qdrant - The All-Around Champion

**Why it wins:**
- 16.6x faster ingestion than Postgres
- 4.4x smaller storage than Postgres
- Sub-10ms vector searches
- 96% success rate (only 4 failures at 10 users)
- Zero-config setup
- Clean, intuitive API
- Beautiful dashboard

**Perfect for:**
- Vector-first applications (search, RAG, recommendations)
- High-throughput document ingestion
- Teams comfortable with NoSQL patterns
- Applications with millions of vectors

**Trade-offs:**
- No SQL (can't JOIN with relational data natively)
- Less mature ecosystem than Postgres/Elasticsearch

**Quote from evaluation**: *"Watching 423K vectors load in 18 seconds (vs 5 minutes for Postgres) felt like the future."*

---

### 🥈 #2: Weaviate - The Production Specialist

**Why it's #2:**
- **Fastest queries**: 560ms p50 (2x faster than competitors)
- **100% success rate**: ONLY database with perfect reliability under load
- Elegant filter API
- GraphQL support
- Production-grade features (multi-tenancy, RBAC)

**Trade-offs:**
- **Slowest ingestion**: 811 emb/sec (40x slower than MongoDB!)
- Explicit schema required
- Longer setup time

**Perfect for:**
- Production apps where query speed >> ingestion speed
- Read-heavy workloads (you ingest once, query millions of times)
- High-availability systems requiring 100% uptime
- RAG applications where latency matters

**Quote from evaluation**: *"Weaviate optimizes for read performance at the cost of write performance. This is the opposite of Milvus - and a valid choice for production."*

---

### 🥉 #3: Postgres + pgvector - The Boring Choice (Compliment!)

**Why it's #3:**
- Familiar SQL syntax
- Integrates seamlessly with existing Postgres infrastructure
- 100% success rate under load
- Can JOIN vector results with relational data
- ORM support (Django, SQLAlchemy)
- No new infrastructure needed

**Trade-offs:**
- 16.6x slower ingestion than Qdrant
- 4.4x larger storage than Qdrant
- Not optimized for pure vector workloads

**Perfect for:**
- Teams already using Postgres
- Hybrid workloads (vectors + relational data)
- Django/Rails applications
- Prototyping and MVPs
- Adding vector search to existing apps without new infrastructure

**Quote from evaluation**: *"Postgres + pgvector is the boring, reliable choice - and that's a compliment. For 99% of use cases, it's fast enough, familiar enough, and practical enough to be the first choice."*

---

### #4: Elasticsearch - The Hybrid King

**Why it's valuable:**
- **100% success rate** under load
- Best-in-class **hybrid search** (vectors + full-text + filters + aggregations)
- Rock-solid reliability
- Mature ecosystem with monitoring, clustering, backups
- Clean Python API with excellent async support

**Trade-offs:**
- JVM overhead (~500MB RAM)
- 4.5x slower ingestion than Qdrant
- Higher resource usage
- Configuration complexity

**Perfect for:**
- Applications needing semantic AND keyword search
- Teams already using Elasticsearch
- Metadata filtering alongside vector similarity
- Production systems requiring operational maturity

**Quote from evaluation**: *"Elasticsearch sits in the sweet spot between general-purpose (Postgres) and specialized (Qdrant), offering the best of both worlds for hybrid search workloads."*

---

### #5: Milvus - The Feature-Rich Powerhouse

**Why it's middle tier:**
- **Fastest ingestion**: 32,496 emb/sec (1.4x faster than Qdrant!)
- Good single-user query performance (700ms p50)
- Production-grade features (distributed mode, RBAC, time travel)

**Why it's not higher:**
- **90% success rate** at 10 users (concerning)
- **15-second cold start** on first query
- High learning curve (integer IDs, dependency hell)
- Confusing APIs (stats lag, no flush())
- Noisy logs in standalone mode
- Least fun to implement

**Unique Strengths** (features we didn't test):

**IMPORTANT**: Our testing was limited to basic vector search on CPU with HNSW indices. Milvus has advanced features we didn't evaluate, including:

- **10 index types**: FLAT, IVF_FLAT, IVF_SQ8, IVF_PQ, HNSW, ScaNN, BIN_FLAT, BIN_IVF_FLAT, SPARSE_INVERTED_INDEX, SPARSE_WAND (we only tested HNSW)
- **GPU indices**: GPU_IVF_FLAT, GPU_IVF_PQ, GPU_BRUTE_FORCE, GPU_CAGRA (we tested on CPU only)
- **Disk-based indices**: DiskANN for billion-scale vectors without RAM limits (we tested in-memory only)
- **Binary vectors**: Specialized support for binary embeddings (we tested dense float vectors only)
- **Multi-vector search**: Query across multiple embedding spaces simultaneously (we tested single-vector search only)
- **Table partitions**: Shard data by tenant/category (we used a single partition)
- **Additional similarity metrics**: JACCARD, HAMMING, BM25 (we only tested cosine similarity)

**Note**: Qdrant and Weaviate also have features we didn't test (e.g., Qdrant supports GPU acceleration, quantization, and on-disk storage; Weaviate supports multi-tenancy and custom modules). Our evaluation focused on basic out-of-box experience, not advanced capabilities.

**Why Milvus's features matter for large-scale production:**
- **GPU support**: Can provide 10-100x faster queries on large datasets (if you have GPUs and configure them properly)
- **Disk indices**: Handle billion-scale vectors without loading everything into RAM (DiskANN)
- **Multiple index types**: Choose the right index for your specific workload (accuracy vs speed trade-offs)
- **Partitions**: Better isolation and performance for multi-tenant applications

**When Milvus is the RIGHT choice:**
- You need to evaluate different index types for your specific workload (not just HNSW)
- Your dataset exceeds RAM (billions of vectors requiring disk-based indices)
- You have GPU infrastructure and want to leverage it for vector search
- You need specialized features like binary vectors or table partitions
- You have ML engineering expertise and can handle complexity
- You're building large-scale AI infrastructure (not a side-project)

**When to avoid:**
- Small datasets (<10M vectors) - overhead not worth it
- High-traffic production APIs - 90% success rate is concerning
- Real-time applications - 15s cold start
- Small teams/prototypes - learning curve too steep

**Quote from evaluation**: *"Milvus is a high-performance specialist for bulk ingestion but struggles with concurrency. For general-purpose vector search, Qdrant or Elasticsearch are safer choices."*

**Fair Assessment**: Milvus is **production-ready for experts** building large-scale AI systems with specific needs (GPU, disk indices, multi-modal). For general-purpose vector search, its complexity outweighs its benefits compared to Qdrant's simplicity.

---

### #6: Redis - The Tactical Cache

**Why it's near the bottom:**
- **55% success rate** at 10 users (45% failures!)
- All data must fit in RAM
- 10-20 second cold start loading RDB
- Poor concurrency performance

**Why it's not dead last:**
- 3.9x faster ingestion than Postgres
- Sub-100ms vector searches (when they work)
- Fast ingestion via pipelined commands

**The REAL use case:**
Redis vectors should be used as a **tactical caching layer** on top of a primary vector DB (Postgres/Qdrant), not standalone:

```
┌─────────────────────────────────┐
│ Primary DB (Postgres/Qdrant)   │
│ • 10M vectors (cold storage)    │
└────────────┬────────────────────┘
             ↓ Sync hot items
┌─────────────────────────────────┐
│ Redis Cache (RAM)               │
│ • 50K hot vectors               │
│ • TTL/LRU eviction              │
│ • Sub-10ms searches             │
└─────────────────────────────────┘
```

**Perfect for:**
- Hot cache layer (10K-100K vectors) with TTL eviction
- E-commerce "people also viewed" during traffic spikes
- Session-based personalization
- LLM embedding cache

**Not for:**
- Standalone vector database
- High concurrent reads (>5 users)
- Large datasets (millions of vectors)

**Quote from evaluation**: *"Redis vectors are not a standalone solution - they're a performance optimization. Think: 'I have Postgres + Redis, let me add hot-path vector caching to Redis' NOT 'I need vector search, let me use Redis'."*

---

### #7: MongoDB - The Write-Only Beast

**Why it's last:**
- **Catastrophic concurrency**: 6.5x latency degradation at 10 users (19.5s p50!)
- **Worst storage overhead**: 12.1x (2.5GB for 207MB embeddings)
- Quirky index lifecycle (create AFTER data insertion)
- Poor documentation for vector search

**Why it's not completely terrible:**
- **Fastest ingestion**: 38,596 emb/sec (1.19x faster than Milvus!)
- 100% success rate (but latency is unacceptable)
- Native BSON array storage
- Familiar API for MongoDB users

**The REAL use case:**
MongoDB should be used as a **write buffer** for bulk ingestion, then sync to a proper vector DB for querying:

```
┌──────────────────────────────────┐
│ MongoDB (Write Buffer)           │
│ • Bulk insert at 38K emb/s       │
│ • Temporary storage              │
└────────────┬─────────────────────┘
             ↓ Sync periodically
┌──────────────────────────────────┐
│ Qdrant/Weaviate (Query Layer)    │
│ • Fast concurrent reads          │
│ • Efficient storage              │
│ • Production reliability         │
└──────────────────────────────────┘
```

**Perfect for:**
- Bulk ingestion with zero concurrent reads
- Write-once, read-rarely patterns
- Teams already running MongoDB for other data

**Not for:**
- Production vector search applications
- Any concurrent read workload
- Storage-constrained environments

**Quote from evaluation**: *"MongoDB is a write specialist that fails at concurrent reads. Use only as a tactical write buffer - bulk insert at incredible speed, then sync to a proper vector database for querying."*

---

## Key Lessons Learned

### 1. Purpose-Built >> General-Purpose (Usually)

Qdrant's 16.6x ingestion advantage over Postgres shows the value of specialized databases. However, Postgres's SQL superpowers make it valuable for hybrid workloads.

**Takeaway**: Use specialized databases when your workload matches their strengths.

### 2. Raw Speed ≠ Production Readiness

MongoDB (38.6K emb/s) and Milvus (32.5K emb/s) are fastest at writes but struggle with concurrency:
- MongoDB: 6.5x latency degradation
- Milvus: 90% success rate

Meanwhile, Weaviate is slowest at writes (811 emb/s) but fastest at reads (560ms) with 100% reliability.

**Takeaway**: Optimize for your bottleneck. Most applications are read-heavy (1 write, millions of reads).

### 3. Storage Efficiency Has Real Costs

Qdrant (1.66x overhead) vs MongoDB (12.1x overhead) is a 7.3x difference:
- 1TB dataset → Qdrant: 1.66TB, MongoDB: 12.1TB
- Cloud storage costs scale linearly

**Takeaway**: At scale, storage efficiency matters as much as query speed.

### 4. Reliability Matters More Than Latency

Redis at 1,165ms with 55% success is worse than Weaviate at 560ms with 100% success. Users can tolerate slow, but they can't tolerate broken.

**Takeaway**: Prioritize reliability over speed. A slow system is usable; a broken system is not.

### 5. Developer Experience Compounds

Qdrant's "zero-config magic" vs Milvus's "integer ID requirement + dependency conflicts" affects:
- Time to first query
- Onboarding new developers
- Debugging efficiency
- Team morale

**Takeaway**: DX debt accumulates. Choose databases that respect your time.

### 6. Cold Start Penalties Are Real

Milvus (15s) and Redis (10-20s) cold starts hurt:
- Dev/test cycles (frequent restarts)
- Serverless deployments
- Microservices (pod churn)

Weaviate/Qdrant/Elasticsearch/Postgres: instant availability.

**Takeaway**: Cold start matters more than benchmarks suggest.

---

## Decision Matrix

### Choose Qdrant if:
- ✅ Vector-first application (search, recommendations, RAG)
- ✅ Need balanced performance (fast reads AND writes)
- ✅ Storage efficiency matters
- ✅ Team comfortable with NoSQL patterns
- ✅ Want the best all-around experience

### Choose Weaviate if:
- ✅ Query speed > ingestion speed (read-heavy)
- ✅ Need 100% reliability under load
- ✅ Ingest infrequently, query constantly
- ✅ Can tolerate slow bulk loading
- ✅ Production app with high availability SLAs

### Choose Postgres if:
- ✅ Already using Postgres
- ✅ Need SQL + vectors in one database
- ✅ Hybrid workloads (relational + vector data)
- ✅ Django/Rails/SQLAlchemy integration
- ✅ Want simplest migration path from existing app

### Choose Elasticsearch if:
- ✅ Need hybrid search (vectors + full-text + filters)
- ✅ Already using Elasticsearch for traditional search
- ✅ Require metadata filtering + aggregations + vector similarity
- ✅ Need operational maturity (monitoring, clustering)

### Choose Milvus if:
- ✅ Bulk ingestion throughput is your #1 priority
- ✅ Offline batch processing (cold start doesn't matter)
- ✅ Have expertise to handle complexity
- ✅ Can tolerate 90% success rate

### Choose Redis if:
- ✅ You're building a hot cache layer (NOT standalone)
- ✅ Have a primary vector DB (Postgres/Qdrant) underneath
- ✅ Small hot dataset (10K-100K vectors)
- ✅ TTL/LRU eviction fits your use case
- ❌ **Never** use as standalone vector search

### Choose MongoDB if:
- ✅ You need maximum write throughput AND zero concurrent reads
- ✅ Write-once, read-rarely pattern
- ✅ Already running MongoDB for other data
- ✅ Can tolerate 12.1x storage overhead
- ❌ **Never** use for production vector search with concurrent reads

---

## Performance Summary Table

| Database          | Ingestion  | Query p50 | Concurrency | Storage  | Setup  | Total                |
|-------------------|------------|-----------|-------------|----------|--------|----------------------|
| **Qdrant**        | 22,954/s   | 1,190ms   | 96% ✅       | 360MB ⭐  | Easy   | **Best**             |
| **Weaviate**      | 811/s ⚠️   | 560ms ⭐   | 100% ⭐      | 641MB    | Medium | **Best for reads**   |
| **Postgres**      | 1,385/s    | 1,156ms   | 100% ⭐      | 1.58GB   | Easy   | **Most familiar**    |
| **Elasticsearch** | 5,117/s    | 1,150ms   | 100% ⭐      | 1.1GB    | Medium | **Hybrid search**    |
| **Milvus**        | 32,496/s ⭐ | 700ms     | 90% ⚠️      | TBD      | Hard   | **Write specialist** |
| **Redis**         | 5,450/s    | 1,165ms   | 55% 🚨      | 1.45GB   | Easy   | **Cache only**       |
| **MongoDB**       | 38,596/s ⭐ | 761ms     | 100%* 🚨    | 2.5GB 🚨 | Medium | **Write buffer**     |

*MongoDB's 100% success is misleading - 6.5x latency degradation at 10 users

---

## Final Recommendations

### For Most Teams: Start with Qdrant
Unless you have a specific reason not to, **Qdrant** is the best all-around choice. It's fast, efficient, reliable, and easy to use. If you need SQL + vectors, use **Postgres**. Both are excellent.

### For Production Read-Heavy Apps: Weaviate
If your application queries vectors 1000x more than it inserts them, **Weaviate's** 2x query speed advantage and 100% reliability make it worth the slower ingestion.

### For Hybrid Search: Elasticsearch
If you need to combine vector similarity with full-text search and complex filters, **Elasticsearch** is the only database that does it well.

### Avoid for Standalone Use: Redis and MongoDB
Both are excellent databases for their primary use cases (caching and document storage), but **not for vector search**. Redis works as a cache layer; MongoDB works as a write buffer. Neither should be your primary vector database.

### Only for Specific Needs: Milvus
Unless you specifically need 32K emb/s ingestion throughput AND have the expertise to handle its quirks, choose Qdrant instead.

---

## Appendix: Raw Performance Data

### Full Comparison Matrix

| Metric                | Postgres | Qdrant  | Redis  | Elasticsearch | Milvus | Weaviate | MongoDB |
|-----------------------|----------|---------|--------|---------------|--------|----------|---------|
| **Ingestion (emb/s)** | 1,385    | 22,954  | 5,450  | 5,117         | 32,496 | 811      | 38,596  |
| **Query p50 (ms)**    | 1,156    | 1,190   | 1,165  | 1,150         | 700    | 560      | 761     |
| **Success @ 10u**     | 100%     | 96%     | 55%    | 100%          | 90%    | 100%     | 100%    |
| **p50 @ 10u (ms)**    | 11,349   | 10,552  | 11,622 | 11,163        | 13,692 | 5,292    | 19,572  |
| **Storage (MB)**      | 1,580    | 360     | 1,450  | 1,100         | TBD    | 641      | 2,500   |
| **Overhead**          | 6.3x     | 1.66x   | 5.7x   | 5.3x          | ?      | 3.1x     | 12.1x   |
| **Memory (GB)**       | 12.6     | 13.0    | 13.75  | 13.6          | 13.6   | 13.7     | 14.2    |
| **Cold Start**        | Instant  | Instant | 10-20s | Instant       | 15s    | Instant  | Instant |
| **Setup Time**        | 2.5h     | 2.5h    | 5h     | 4h            | 4h+    | 4h       | 3h      |
| **Learning Curve**    | Medium   | Low     | Low    | Medium        | High   | Medium   | Medium  |
| **Fun Factor**        | ⭐⭐⭐⭐     | ⭐⭐⭐⭐⭐   | ⭐⭐⭐    | ⭐⭐⭐⭐          | ⭐⭐     | ⭐⭐⭐      | ⭐⭐      |

### Individual Evaluation Links

- [Postgres Evaluation](./POSTGRES_EVALUATION.md) - The boring, reliable choice
- [Qdrant Evaluation](./QDRANT_EVALUATION.md) - The all-around champion
- [Redis Evaluation](./REDIS_EVALUATION.md) - The cache specialist
- [Elasticsearch Evaluation](./ELASTICSEARCH_EVALUATION.md) - The hybrid search king
- [Milvus Evaluation](./MILVUS_EVALUATION.md) - The write specialist
- [Weaviate Evaluation](./WEAVIATE_EVALUATION.md) - The production champion
- [MongoDB Evaluation](./MONGODB_EVALUATION.md) - The write-only beast

---

**Conclusion**: After testing 7 databases with 423,741 embeddings, **Qdrant** emerges as the clear winner for most use cases. **Weaviate** is best for production read-heavy workloads. **Postgres** is best for teams already using Postgres. **Elasticsearch** is best for hybrid search. **Milvus** is best for bulk ingestion specialists. **Redis** and **MongoDB** are best avoided for standalone vector search.

**Personal Favorite**: Qdrant. The combination of speed, storage efficiency, reliability, and developer experience makes it the obvious choice for new vector search projects.