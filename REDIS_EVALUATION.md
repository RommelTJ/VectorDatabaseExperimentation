# Redis Stack - Performance Evaluation

**Database**: Redis Stack 7.4.6 (with RediSearch 2.10.20)
**Dataset**: 80 knitting pattern PDFs (423,741 embeddings, 128 dimensions)
**Hardware**: Docker Desktop on macOS (16GB RAM limit, CPU-only)
**Date**: 2025-10-11

---

## Setup Complexity

**Docker Setup**: ⭐⭐⭐⭐⭐ (5/5)
Single line in docker-compose.yml. Redis Stack Docker image includes RediSearch module out of the box.

**Index Definition**: ⭐⭐⭐ (3/5)
RediSearch FT.CREATE syntax is more verbose than expected. HNSW parameters require understanding Redis-specific conventions. Binary vector encoding (struct.pack) adds complexity vs other databases.

**Client Library**: ⭐⭐⭐⭐ (4/5)
Used `redis-py` (async) - mature and well-documented. Direct command execution with execute_command() gives flexibility but feels lower-level than purpose-built vector DB clients.

---

## Performance Results

### Ingestion Performance
- **Total embeddings**: 423,741 vectors
- **Ingestion time**: 77.75 seconds
- **Throughput**: 5,450 embeddings/second
- **Average per PDF**: 0.97 seconds
- **Speedup vs Postgres**: **3.9x faster** (Redis: 77s vs Postgres: 305s)

**Note**: Redis uses pipelined HSET commands for batch inserts - significantly faster than Postgres batch inserts.

### Query Latency (Single User)

#### Cold Cache (first queries after restart)
| k   | p50      | p95      | p99      | Success |
|-----|----------|----------|----------|---------|
| 5   | 1,152 ms | 2,090 ms | 2,853 ms | 20/20   |
| 10  | 1,139 ms | 1,263 ms | 1,299 ms | 20/20   |
| 20  | 1,177 ms | 1,336 ms | 1,366 ms | 20/20   |

#### Warm Cache (repeated queries)
| k   | p50      | p95      | p99      | Success |
|-----|----------|----------|----------|---------|
| 5   | 1,170 ms | 1,247 ms | 1,253 ms | 20/20   |
| 10  | 1,165 ms | 1,204 ms | 1,210 ms | 20/20   |
| 20  | 1,146 ms | 1,341 ms | 1,419 ms | 20/20   |

**Important Note**: ~1,100-1,200ms of query time is ColPali embedding generation (CPU-bound).
Actual Redis vector search is estimated **<100ms**, similar to Postgres.

**Cold start penalty**: First query shows significant spike (2,135ms) as Redis loads index structures into memory.

### Concurrent Load Performance

| Users | Total Queries | Success | Time     | QPS  | p50       | p95       | p99       |
|-------|---------------|---------|----------|------|-----------|-----------|-----------|
| 2     | 20            | 20/20   | 24.44s   | 0.82 | 2,179 ms  | 2,911 ms  | 2,913 ms  |
| 5     | 50            | 50/50   | 58.14s   | 0.86 | 5,552 ms  | 5,805 ms  | 5,806 ms  |
| 10    | 100           | **55/100** | 121.38s  | 0.45 | 11,622 ms | 16,914 ms | 17,100 ms |

**⚠️ Critical Issue**: **45% failure rate** at 10 concurrent users. Queries timeout after 15+ seconds, suggesting connection pool exhaustion or resource contention.

**Observations**:
- Perfect reliability up to 5 concurrent users
- Catastrophic degradation at 10 users (45% failures)
- Latency increases linearly but QPS drops significantly
- Much worse than Postgres (100% success at 10 users)

### Memory Usage

**During sequential queries (20 queries)**:
- **Peak RAM**: 13.75 GB (87.6% of 16GB limit)
- **Mean RAM**: 13.66 GB (87.1%)
- **Delta**: +150 MB during query workload

**Under concurrent load (5 users)**:
- **Peak RAM**: 13.76 GB (87.7%)
- **Mean RAM**: 13.68 GB (87.2%)
- **Delta**: +153 MB

**Memory breakdown**:
- ColPali model: ~11.9 GB
- **Redis dataset**: ~1.5 GB (all vectors + metadata in RAM)
- Application overhead: ~0.35 GB

**Critical**: Redis requires **all data in memory**. With 423K embeddings at ~1.5GB, you're consuming significantly more RAM than Postgres (which uses ~0.5GB working set + disk storage).

### Storage Footprint

| Component              | Size    | Notes                                    |
|------------------------|---------|------------------------------------------|
| Redis volume (RDB dump)| 1.45 GB | Compressed snapshot of in-memory data    |
| Embeddings cache       | 217 MB  | Raw numpy files (baseline)               |
| HuggingFace cache      | 11.93 GB| ColPali model + dependencies             |
| Backend Docker image   | 1.2 GB  | Python + FastAPI + dependencies          |
| **Index overhead**     | **1.23 GB** | Beyond raw embeddings (5.7x multiplier) |

**Startup time**: Loading 1.45GB RDB file into memory takes **10-20 seconds** - noticeably slower than Postgres startup.

---

## Unique Features & Observations

### Strengths
- **Blazingly fast ingestion**: 3.9x faster than Postgres due to pipelined commands
- **Simple data model**: Hash-based storage is conceptually simple
- **Redis ecosystem**: Can combine vector search with Redis caching, pub/sub, streams in one system
- **Familiar commands**: If you already use Redis, adding vector search feels natural
- **Low query latency**: Sub-100ms vector searches (when ColPali overhead excluded)

### Limitations
- **Memory-bound scaling**: All data must fit in RAM. For 423K vectors, that's ~1.5GB. Scale linearly with dataset size.
- **Poor concurrent performance**: 45% failure rate at 10 concurrent users is unacceptable for production
- **Slow cold starts**: Loading RDB from disk takes 10-20 seconds on restarts
- **Connection timeouts**: Default Redis timeout (5s) insufficient for concurrent vector searches
- **No automatic sharding**: Redis Cluster doesn't natively support vector search - manual partitioning required
- **Limited query capabilities**: No JOIN-like operations with metadata, no complex filtering

### Surprises
- **Ingestion speed**: Expected in-memory to be fast, but 3.9x speedup over Postgres was impressive
- **Concurrent failure rate**: 45% failures at 10 users was shocking - suggests Redis isn't tuned for this workload
- **Memory usage**: 13.75 GB total (1.5GB for vectors) pushes Docker Desktop limits
- **Deduplication complexity**: Had to manually implement pdf_id deduplication (fetch 3x, filter) - not built-in
- **Startup latency**: Noticeable 10-20 second pause while Redis loads RDB into memory

---

## Developer Experience

### Setup Time
- **Docker service**: 3 minutes
- **Index creation**: 15 minutes (understanding FT.CREATE syntax)
- **Adapter implementation**: 3 hours (binary encoding, result parsing, deduplication)
- **Full ingestion**: 1.5 minutes (fast!)
- **Debugging concurrent failures**: 1 hour
- **Total**: ~5 hours from zero to functional (with caveats)

### Pain Points
- **Binary vector encoding**: Manual struct.pack() for FLOAT32 arrays felt low-level
- **Result parsing**: FT.SEARCH returns flat arrays that need manual parsing into dicts
- **Timeout configuration**: Default 5s timeout insufficient - had to increase to 15s+ for concurrent loads
- **Deduplication logic**: Had to implement pdf_id deduplication manually (unlike Qdrant's built-in support)
- **Connection pool tuning**: Unclear how to properly configure Redis connection pooling for concurrent vector workloads
- **No rollback**: Redis lacks transactions for vector operations - errors leave partial data

### Pleasant Surprises
- **Pipeline performance**: Batch inserts via pipeline were impressively fast
- **Index creation**: Instant (vs minutes for Postgres) - Redis builds indexes incrementally
- **Simple key schema**: patterns:{pdf_id}:{page}:{patch} made debugging easy
- **SCAN for deletion**: Pattern-based key scanning worked well for bulk deletes

### Documentation Quality
- **RediSearch docs**: Good coverage but assumes Redis knowledge
- **Vector search examples**: Sparse - had to piece together from multiple sources
- **Community resources**: Limited Stack Overflow answers for vector search specific issues
- **Python client docs**: Excellent for general Redis, weak for RediSearch specifics

---

## Evaluation Metrics

### Practicality: ⭐⭐ (2/5)
**Would I use this again?** Probably not, except for specific niches.

Redis's **45% failure rate** at 10 concurrent users is a deal-breaker for production use. The memory requirement (all data in RAM) limits scalability, and the slow cold start is problematic for containerized deployments.

**Best for**:
- Small datasets (<1M vectors) where everything fits comfortably in RAM
- Teams already heavily invested in Redis infrastructure
- Use cases where vector search is secondary to Redis's other features (caching, pub/sub)
- Scenarios with low concurrent query load (<5 users)
- Prototypes where ingestion speed matters more than query reliability

**Not ideal for**:
- Production workloads with >5 concurrent users
- Large datasets (millions of vectors → expensive RAM)
- Applications requiring high availability (cold start latency)
- Cost-sensitive projects (RAM is expensive vs disk)
- Any scenario where 45% failure rate is unacceptable

### Learnings: ⭐⭐⭐⭐ (4/5)
**Unique insights gained**:

1. **In-memory trade-off**: Blazing fast ingestion but memory-constrained scaling
2. **Concurrent performance**: Redis isn't optimized for concurrent vector search - connection/timeout issues
3. **Cold start matters**: 10-20s startup latency matters more than I expected for microservices
4. **Pipeline power**: Redis pipelining for batch operations is significantly faster than traditional batch inserts
5. **Manual optimization burden**: Deduplication, timeout tuning, connection pooling all require manual implementation
6. **Memory overhead**: 1.5GB for 423K vectors (128d) - higher than expected, 5.7x the raw embeddings

**Would have learned more with**: Better understanding of Redis Cluster vector search support (if any).

### Fun: ⭐⭐⭐ (3/5)
**How enjoyable was this?**

Mixed experience. Fast ingestion was satisfying, but the concurrent failure debugging was frustrating. Binary encoding felt unnecessarily low-level compared to other vector DBs. The "it should work but doesn't at scale" issue dampened the experience.

**Highlight**: Watching 423K vectors ingest in 77 seconds was impressive.

**Lowlight**: Watching 45% of concurrent queries fail with timeout errors.

---

## Final Thoughts

Redis Stack with RediSearch is **fast when it works**, but the **45% concurrent failure rate** and **memory-bound scaling** make it a risky choice for production vector search. The "all data in RAM" architecture is both its strength (fast access) and fatal flaw (expensive, limited scale).

For datasets that fit comfortably in RAM (<1M vectors) with low concurrent load (<5 users), Redis can work. But for most applications, **Postgres + pgvector** offers better reliability, lower cost, and easier scaling.

**Recommendation**: Skip Redis for vector search unless you're already using Redis extensively and have a small, read-light dataset. The operational complexity and failure modes outweigh the ingestion speed benefits.

---

## Raw Benchmark Data

Detailed JSON results available at:
- `benchmark_results.json` - Query latency measurements
- `load_test_results.json` - Concurrent user simulations (note 45% failures at 10 users)
- `memory_monitoring_results.json` - RAM usage tracking
