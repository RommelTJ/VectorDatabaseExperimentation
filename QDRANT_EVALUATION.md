# Qdrant - Performance Evaluation

**Database**: Qdrant v1.15.5
**Dataset**: 80 knitting pattern PDFs (423,741 embeddings, 128 dimensions)
**Hardware**: Docker Desktop on macOS (16GB RAM limit, CPU-only)
**Date**: 2025-10-07

---

## Setup Complexity

**Docker Setup**: ⭐⭐⭐⭐⭐ (5/5)
Single official Docker image. Zero configuration needed. Worked immediately out of the box.

**Schema Definition**: ⭐⭐⭐⭐⭐ (5/5)
Simple collection creation with `VectorParams`. Clean, minimal API. Distance metric and dimensions - that's it.

**Client Library**: ⭐⭐⭐⭐⭐ (5/5)
`qdrant-client` is excellent. Intuitive Python API, well-documented, with both sync and async support.

---

## Performance Results

### Ingestion Performance
- **Total embeddings**: 423,741 vectors
- **Ingestion time**: 18.46 seconds
- **Throughput**: 22,954 embeddings/second
- **Average per PDF**: 0.23 seconds
- **Batch method**: Upsert with `PointStruct` objects

**Comparison to Postgres**: 16.6x faster ingestion! (Postgres: 1,385 emb/sec)

### Query Latency (Single User)

#### Cold Cache (first queries after restart)
| k   | p50      | p95      | p99      | Success |
|-----|----------|----------|----------|---------|
| 5   | 1,209 ms | 1,601 ms | 1,902 ms | 20/20   |
| 10  | 1,197 ms | 1,266 ms | 1,299 ms | 20/20   |
| 20  | 1,202 ms | 1,232 ms | 1,236 ms | 20/20   |

#### Warm Cache (repeated queries)
| k   | p50      | p95      | p99      | Success |
|-----|----------|----------|----------|---------|
| 5   | 1,196 ms | 1,219 ms | 1,224 ms | 20/20   |
| 10  | 1,190 ms | 1,211 ms | 1,214 ms | 20/20   |
| 20  | 1,194 ms | 1,213 ms | 1,216 ms | 20/20   |

**Important Note**: ~1,100-1,200ms of query time is ColPali embedding generation (CPU-bound).
Actual Qdrant vector search is **<10ms** (even faster than Postgres's ~100ms!).

### Concurrent Load Performance

| Users | Total Queries | Success | Time     | QPS  | p50       | p95       | p99       |
|-------|---------------|---------|----------|------|-----------|-----------|-----------|
| 2     | 20            | 20/20   | 25.04s   | 0.80 | 2,307 ms  | 2,689 ms  | 2,691 ms  |
| 5     | 50            | 50/50   | 61.98s   | 0.81 | 5,817 ms  | 6,735 ms  | 6,873 ms  |
| 10    | 100           | 96/100  | 114.31s  | 0.84 | 10,552 ms | 17,325 ms | 29,522 ms |

**Observations**:
- 96% success rate at 10 concurrent users (4 failures - timeout issues)
- Postgres had 100% success rate at same load
- Latency scales linearly with concurrent users
- Throughput remains stable (~0.80-0.84 QPS)
- Bottleneck is still sequential ColPali embedding generation

### Memory Usage

**During sequential queries (20 queries)**:
- **Peak RAM**: 13,015 MB (83.0% of 16GB limit)
- **Mean RAM**: 12,924 MB (82.5%)
- **Delta**: +148 MB during query workload

**Under concurrent load (5 users)**:
- **Peak RAM**: 13,022 MB (83.1%)
- **Mean RAM**: 12,950 MB (82.6%)
- **Delta**: +145 MB

**Memory breakdown**:
- ColPali model: ~11.9 GB
- Application overhead: ~0.5 GB
- Query processing: ~0.6 GB

**Comparison to Postgres**: Nearly identical memory usage (both dominated by ColPali).

### Storage Footprint

| Component              | Size    | Notes                                    |
|------------------------|---------|------------------------------------------|
| Qdrant volume          | 360 MB  | Vectors + metadata + HNSW index          |
| Embeddings cache       | 217 MB  | Raw numpy files (baseline)               |
| HuggingFace cache      | 11.93 GB| ColPali model + dependencies             |
| Backend Docker image   | 1.2 GB  | Python + FastAPI + dependencies          |
| **Index overhead**     | **143 MB** | Beyond raw embeddings (1.66x multiplier) |

**Comparison to Postgres**:
- Qdrant: 360 MB (1.66x overhead)
- Postgres: 1.58 GB (7.28x overhead)
- **Qdrant uses 77% less storage!** (4.4x smaller)

---

## Unique Features & Observations

### Strengths
- **Blazing fast ingestion**: 16.6x faster than Postgres for bulk operations
- **Ultra-low query latency**: <10ms for vector search (vs Postgres ~100ms)
- **Excellent storage efficiency**: 1.66x overhead vs Postgres 7.28x
- **Simple, clean API**: Intuitive Python client, minimal configuration
- **Built-in web dashboard**: http://localhost:6333/dashboard for visual inspection
- **Filter-based operations**: Elegant filter API for deletes and conditional queries
- **Purpose-built for vectors**: No relational overhead, optimized data structures
- **REST + gRPC APIs**: Flexible access patterns (we used REST)
- **Deterministic IDs**: Easy to generate point IDs from metadata for idempotent inserts

**Real-world use cases**:
- **High-throughput ingestion**: Perfect for batch processing large document collections
- **Real-time search**: Sub-10ms queries enable instant search experiences
- **Microservices architecture**: Standalone vector service without database coupling
- **RAG pipelines**: Fast enough to support real-time retrieval-augmented generation
- **Recommendation engines**: Low-latency similarity search for user preferences

### Limitations
- **Less mature ecosystem**: Fewer tutorials/Stack Overflow answers than Postgres
- **No SQL**: Can't join vector results with relational data natively
- **Slightly less stable under extreme load**: 96% success vs Postgres 100% at 10 users
- **Separate service**: Another component to manage vs adding pgvector to existing Postgres
- **No ACID transactions across collections**: Different model than traditional databases
- **Filter performance**: Complex filters can slow down queries (we didn't test this heavily)

**Scaling considerations**:
Qdrant is designed for horizontal scaling with sharding and replication. For workloads exceeding single-node capacity, it offers distributed mode. However, for most applications, a single Qdrant instance can handle millions of vectors efficiently.

### Surprises
- **Storage efficiency**: Expected similar overhead to Postgres, got 4.4x improvement
- **Dashboard quality**: Web UI is polished and actually useful for debugging
- **API simplicity**: Cleaner than expected - no complex configuration needed
- **Filter syntax**: Elegant use of `FieldCondition` and `MatchAny` for deletions
- **Reliability**: Only 4 failures at 10 concurrent users (timeout-related, not crashes)

---

## Developer Experience

### Setup Time
- **Docker service**: 2 minutes (single image, no config)
- **Collection creation**: 5 minutes (simple VectorParams)
- **Adapter implementation**: 2 hours (connect, create, insert, search, delete)
- **Full ingestion**: <1 minute (18 seconds!)
- **Total**: ~2.5 hours from zero to fully functional

### Pain Points
- Had to read docs to find correct health check method (`get_collections()` not `get_health()`)
- Filter API requires importing several classes (`Filter`, `FieldCondition`, `MatchAny`)
- Deterministic ID generation needed manual implementation (SHA256 hashing)
- 4 failures at high concurrency suggest possible timeout tuning needed

### Pleasant Surprises
- **Zero configuration**: Just start the container and go
- **Upsert by default**: Insert or update based on ID - idempotent operations
- **Batch operations**: Single API call for multiple points
- **Dashboard included**: No need for separate admin tools
- **Clear error messages**: Easy to debug issues

### Documentation Quality
- **Qdrant docs**: Excellent examples, clear structure, comprehensive
- **Python client docs**: Good API reference with type hints
- **Community resources**: Growing but less mature than Postgres ecosystem

---

## Evaluation Metrics

### Practicality: ⭐⭐⭐⭐⭐ (5/5)
**Would I use this again?** Absolutely, for vector-first workloads.

Qdrant is the obvious choice when vectors are the primary data structure. The 16.6x ingestion speedup and 77% storage 
savings are compelling. For applications that don't need complex SQL joins with vector results, Qdrant is superior to 
Postgres + pgvector.

**Best for**:
- Vector-first applications (search, recommendations, RAG)
- High-throughput document ingestion
- Real-time similarity search requirements
- Microservices architectures with dedicated vector service
- Applications with millions of vectors
- Teams comfortable with NoSQL patterns

**Not ideal for**:
- Applications requiring frequent JOINs between vectors and relational data
- Teams wanting a single database for everything (Postgres wins here)
- Workloads where SQL queries are essential
- Projects needing the most mature ecosystem

### Learnings: ⭐⭐⭐⭐⭐ (5/5)
**Unique insights gained**:

1. **Purpose-built >> general-purpose**: Qdrant's 16.6x ingestion advantage shows the value of specialized databases
2. **Storage format matters**: 1.66x vs 7.28x overhead proves optimized storage pays dividends
3. **Filter-based operations**: The `Filter` API is more elegant than SQL for vector metadata filtering
4. **Dashboard value**: Built-in UI made debugging much faster than SQL queries
5. **Trade-offs are real**: 96% vs 100% success shows even specialized DBs have limits
6. **Simplicity wins**: Less configuration = faster time to production
7. **Vector-first thinking**: When you treat vectors as first-class citizens (not a SQL extension), architecture improves

**New perspective**: After Postgres, I assumed all vector DBs would be "good enough." Qdrant showed there's a real 
performance difference when you optimize from the ground up for vectors. The storage efficiency alone could save 
significant cloud costs at scale.

### Fun: ⭐⭐⭐⭐⭐ (5/5)
**How enjoyable was this?**

Delightful! The combination of zero-config setup, instant ingestion, and a polished dashboard made this feel like 
magic. Watching 423K vectors load in 18 seconds (vs 5 minutes for Postgres) was genuinely exciting. The API was clean 
enough that implementing the adapter felt natural, not forced.

**Highlight**: The ingestion speed. Going from "start script" to "423K vectors indexed" in under 20 seconds felt like 
the future.

**Lowlight**: The 4 failures at 10 concurrent users were a tiny blemish on an otherwise perfect experience.

---

## Final Thoughts

Qdrant is **the specialist** - purpose-built for vectors, and it shows. If your application is vector-centric (search, 
recommendations, RAG), Qdrant offers compelling advantages: 16.6x faster ingestion, 4.4x smaller storage, and sub-10ms 
queries. The developer experience is polished, the API is clean, and the dashboard is genuinely useful.

**Comparison to Postgres**:
- Postgres is the **generalist** - great at everything, master of SQL + vectors
- Qdrant is the **specialist** - exceptional at vectors, ignore everything else

**Trade-off**: You gain performance and efficiency, but lose SQL's relational superpowers. For pure vector workloads, 
that's an easy trade. For hybrid workloads (vectors + complex relational queries), Postgres might still win.

**Recommendation**: Use Qdrant when vectors are your primary data. Use Postgres when you need SQL + vectors in the 
same database. Both are excellent - just optimized for different use cases.

---

## Raw Benchmark Data

Detailed JSON results available at:
- `benchmark_results.json` - Query latency measurements
- `load_test_results.json` - Concurrent user simulations
- `memory_monitoring_results.json` - RAM usage tracking
