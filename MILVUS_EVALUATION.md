# Milvus Vector Database Evaluation

**Date:** October 25, 2025
**Version:** Milvus v2.4.15
**Test Dataset:** 80 knitting pattern PDFs, 423,741 ColPali embeddings (128 dimensions)

## Executive Summary

Milvus delivers **exceptional ingestion performance** (32,496 emb/s - 1.4x faster than Qdrant, 23x faster than Postgres), making it the fastest database tested for write-heavy workloads. However, this raw speed comes at a cost: a **steep learning curve**, **confusing API quirks**, **poor concurrency handling** (90% success rate vs 96-100% for others), and a **15-second cold start penalty**. While Milvus excels at bulk ingestion, its developer experience and reliability under load fall short of more mature alternatives like Qdrant and Elasticsearch.

## Setup Experience

### Docker Configuration
```yaml
milvus:
  profiles: ["milvus"]
  image: milvusdb/milvus:v2.4.15
  command: milvus run standalone
  ports:
    - "19530:19530"
    - "9091:9091"
  environment:
    - ETCD_USE_EMBED=true
    - COMMON_STORAGETYPE=local
  volumes:
    - milvus-data:/var/lib/milvus
```

### Dependency Management ⚠️

**Major Issue:** Milvus has strict dependency requirements that conflict with common package versions.

```python
# Had to pin marshmallow to 3.x due to environs dependency
pymilvus==2.4.9
marshmallow>=3.13.0,<4.0.0  # 4.x breaks environs
environs>=9.5.0
protobuf>=3.20.0
grpcio>=1.49.1
```

**Error encountered:**
```
AttributeError: module 'marshmallow' has no attribute '__version_info__'
```

This required debugging pip dependencies and manually pinning marshmallow to version 3.x. Other databases (Qdrant, Elasticsearch, Postgres) had zero dependency conflicts.

### Logging Noise 📢

Milvus standalone mode produces **extremely verbose and noisy logs**, especially on startup:

```
[WARN] invalid metrics of DataNode was found
[WARN] node not found
[WARN] grpc: connection refused
[WARN] failed to verify node session
```

These warnings are harmless (internal health checks for distributed components that don't exist in standalone mode) but create a poor first impression and make debugging real issues difficult.

**Verdict:** Setup complexity is **moderate to high** due to dependency conflicts and confusing logs.

## Implementation Experience

### Schema Definition - Integer ID Gotcha ⚠️

Milvus's simple API (`MilvusClient.create_collection()`) automatically creates a schema, but with a critical quirk:

```python
# Schema created by MilvusClient
{
    'auto_id': False,  # ← Requires manual IDs!
    'fields': [
        {'name': 'id', 'type': DataType.INT64, 'is_primary': True},
        {'name': 'vector', 'type': DataType.FLOAT_VECTOR, 'params': {'dim': 128}}
    ],
    'enable_dynamic_field': True  # ← At least this is helpful!
}
```

**Problem:** Unlike other databases where we use string IDs like `{pdf_id}_{page_num}_{patch_index}`, Milvus requires **integer primary keys**. This forced us to hash compound keys:

```python
compound_key = f"{pdf_id}_{page_num}_{patch_index}"
hash_int = int(hashlib.md5(compound_key.encode()).hexdigest()[:16], 16)
int64_id = hash_int % (2**63)  # Convert to signed int64
```

**Comparison:**
- Postgres/Elasticsearch: String IDs work naturally
- Qdrant: UUID/string IDs work naturally
- Redis: String keys work naturally
- Milvus: Must hash to int64 (extra complexity)

### Collection Loading - 15 Second Cold Start 🐌

On first query after collection creation, Milvus takes **~15 seconds** to return results:

```bash
$ curl -X POST http://localhost:8000/api/search/text \
  -d '{"query": "cable knit", "limit": 5}'
# ... 15 seconds later ...
{"results": [...]}
```

This is Milvus loading the collection into memory and building HNSW index structures. Subsequent queries are fast (~700ms dominated by ColPali).

**Comparison:**
- Milvus: **15 seconds** cold start
- Qdrant: Instant
- Elasticsearch: Instant
- Postgres: Instant

### Stats API Confusion 📊

The `get_collection_stats()` API returns misleading results:

```python
# Immediately after inserting 6,186 entities
stats = client.get_collection_stats('patterns')
print(stats['row_count'])  # Output: 0 ❌

# But search works fine!
results = client.search(...)  # Returns actual results ✅
```

Data is present and searchable, but stats don't update immediately. This created confusion during testing and required workarounds to verify ingestion success.

### API Inconsistencies

**Missing flush():**
```python
# MilvusClient doesn't have flush()
self.client.flush(collection_name)  # AttributeError! ❌

# Lower-level API has it, but MilvusClient doesn't
```

**Search result structure:**
```python
# Results is a list of lists (one per query vector)
results = client.search(data=[vector], ...)
for hit in results[0]:  # Must index into first query
    # Entity fields are nested unpredictably
    pdf_id = hit.get('entity', {}).get('pdf_id') or hit.get('pdf_id')
```

The result structure is awkward compared to Qdrant's clean dictionary format or Elasticsearch's `_source` convention.

## Performance Evaluation

### Ingestion Speed 🚀

**Result: 32,496 embeddings/sec** - **FASTEST database tested!**

```
============================================================
INGESTION COMPLETE
============================================================
Database: milvus
PDFs processed: 80
Total embeddings: 423,741
Total time: 13.04 seconds
Average speed: 32,496.5 embeddings/sec
============================================================
```

**Comparison:**
- Milvus: **32,496 emb/s** 🏆
- Qdrant: 22,954 emb/s (1.4x slower)
- Redis: 5,450 emb/s (6.0x slower)
- Elasticsearch: 5,117 emb/s (6.4x slower)
- Postgres: 1,385 emb/s (23.5x slower!)

**Analysis:** Milvus's ingestion performance is exceptional. This makes it ideal for:
- Initial bulk loading of large datasets
- High-throughput write scenarios
- ETL pipelines with massive vector ingestion

### Query Latency (Single User) ✅

```
============================================================
BENCHMARK SUMMARY
============================================================
Round                  k Success      p50      p95      p99
------------------------------------------------------------
Cold Cache (k=5)       5  20/20   758.74ms 1192.88ms 1321.81ms
Cold Cache (k=10)     10  20/20   715.27ms 1075.96ms 1087.01ms
Cold Cache (k=20)     20  20/20   689.19ms 1097.02ms 1129.39ms
Warm Cache (k=5)       5  20/20   694.80ms 1084.21ms 1171.96ms
Warm Cache (k=10)     10  20/20   691.76ms 1094.12ms 1098.07ms
Warm Cache (k=20)     20  20/20   699.47ms 1117.31ms 1117.41ms
============================================================
```

**Analysis:**
- p50 latency: ~700ms (excellent, dominated by ColPali embedding generation)
- p95 latency: ~1,100ms (good consistency)
- p99 latency: ~1,130ms (no long tail issues)
- Actual Milvus search: <10ms (estimated after subtracting ColPali time)

Single-user performance is strong and comparable to Qdrant/Elasticsearch.

### Concurrency Performance ⚠️

```
======================================================================
LOAD TEST SUMMARY
======================================================================
Users Requests Success    Time     QPS      p50      p95      p99
----------------------------------------------------------------------
    2       20   20/20   35.26s    0.57 3280.45ms 4134.74ms 4141.08ms
    5       50   50/50   85.90s    0.58 8186.30ms 9739.27ms 17455.41ms
   10      100   90/100 175.58s    0.51 13691.91ms 39013.63ms 53951.86ms
======================================================================
```

**Problem:** At 10 concurrent users, Milvus exhibits:
- **90% success rate** (10 failures out of 100 requests)
- **13.7 second** p50 latency (vs ~1-2s for other DBs)
- **54 second** p99 latency (unacceptable for real-time apps)

**Comparison:**
- Postgres: 100% success rate
- Elasticsearch: 100% success rate
- Qdrant: 96% success rate (4 failures)
- Redis: 55% success rate (45 failures)
- **Milvus: 90% success rate** (10 failures)

**Root Cause:** Likely resource contention or connection pool limits in standalone mode. The single-container deployment may not handle concurrent connections well.

**Mitigation:** Production deployments would use distributed mode with multiple query nodes, which should improve concurrency. However, this evaluation focuses on the out-of-box experience.

### Memory Usage

```
Memory Statistics:
  Samples: 1144
  Peak usage: 13,610.99 MB (86.80%)
  Mean usage: 13,517.72 MB (86.19%)
  Memory delta: 160.88 MB
```

**Analysis:**
- Peak memory: 13.6 GB (normal, dominated by ColPali model at ~12.5 GB)
- Memory delta: 161 MB (Milvus-specific overhead is minimal)
- No memory leaks observed

### Storage Efficiency

**Not measured in detail** (would require inspecting volume size), but Milvus uses:
- RocksDB for metadata storage
- Custom vector index format optimized for HNSW

Based on documentation, storage overhead should be similar to Qdrant (low) rather than Postgres (high).

## Notable Strengths

### 1. Exceptional Ingestion Speed 🚀
32,496 emb/s makes Milvus the **clear winner** for bulk loading and write-heavy workloads.

### 2. Dynamic Schema Support
`enable_dynamic_field: True` allows inserting arbitrary metadata fields without pre-defining schema:

```python
doc = {
    "id": int64_id,
    "vector": vector,
    "pdf_id": "...",      # Dynamic field
    "page_num": 0,        # Dynamic field
    "patch_index": 0,     # Dynamic field
    "title": "...",       # Dynamic field
    "custom_field": "..." # Works! No schema changes needed
}
```

This flexibility is helpful during prototyping.

### 3. Production-Grade Features
- HNSW indexing with tunable parameters (M, efConstruction)
- Distributed architecture (when not in standalone mode)
- Compaction and index optimization
- Role-based access control (RBAC)
- Time travel queries

## Notable Weaknesses

### 1. High Learning Curve 📚
- Integer ID requirement (not string IDs like other DBs)
- Must understand `auto_id: False` vs `True` behavior
- Dependency management issues (marshmallow conflict)
- Confusing API (stats lag, no flush(), nested result structures)
- Verbose/noisy logs in standalone mode

### 2. Poor Concurrency (90% Success) ⚠️
At 10 concurrent users:
- 10% failure rate
- 13.7s p50 latency (vs ~1-2s for competitors)
- 54s p99 latency

This makes Milvus unsuitable for high-traffic applications without additional tuning or distributed deployment.

### 3. Cold Start Penalty 🐌
15-second delay on first query after collection creation is problematic for:
- Dev/test environments (frequent restarts)
- Serverless deployments (cold starts)
- Applications requiring instant availability

### 4. Developer Experience
Compared to Qdrant's "zero-config magic" or Elasticsearch's well-documented APIs, Milvus feels:
- More manual (hash IDs, understand schema intricacies)
- Less intuitive (stats don't work as expected)
- Rougher around the edges (dependency conflicts, noisy logs)

## Comparison with Other Databases

| Metric | Milvus | Qdrant | Elasticsearch | Redis | Postgres |
|--------|--------|--------|---------------|-------|----------|
| **Ingestion** | **32,496 emb/s** 🏆 | 22,954 | 5,117 | 5,450 | 1,385 |
| **Query p50** | ~700ms | ~1,190ms | ~1,150ms | ~1,165ms | ~1,156ms |
| **Concurrency (10u)** | 90% ⚠️ | 96% | 100% ✅ | 55% ❌ | 100% ✅ |
| **Cold Start** | 15s ⚠️ | Instant | Instant | 10-20s | Instant |
| **Memory** | 13.6 GB | 13.0 GB | 13.6 GB | 13.75 GB | 12.6 GB |
| **Learning Curve** | High 📚 | Low ✅ | Medium | Low | Medium |
| **Developer XP** | Rough | Excellent | Good | Good | Excellent |

## Use Case Recommendations

### ✅ Good Fit For:
- **Bulk ingestion workloads** - Milvus is unmatched at 32K emb/s
- **Batch ETL pipelines** - Load millions of vectors efficiently
- **Large-scale offline processing** - Where cold start doesn't matter
- **Teams with Milvus expertise** - Willing to invest in learning curve

### ⚠️ Questionable For:
- **High-traffic production APIs** - 90% concurrency success is concerning
- **Real-time applications** - 15s cold start is problematic
- **Small teams/prototypes** - Learning curve vs Qdrant's simplicity
- **Dev/test environments** - Noisy logs and cold starts are annoying

### ❌ Poor Fit For:
- **Mission-critical apps** - Elasticsearch/Postgres have 100% reliability
- **Serverless deployments** - Cold start penalty is unacceptable
- **Beginners** - Qdrant is much easier to get started with

## Final Ratings

### Practicality: ⭐⭐⭐ (3/5)
**Would I use Milvus again?** Only for specific use cases.

**Pros:**
- Blazing fast ingestion (32K emb/s is hard to ignore)
- Production-ready features (RBAC, distributed mode, time travel)

**Cons:**
- High learning curve (integer IDs, dependency hell, confusing APIs)
- Poor concurrency (90% success rate is risky for production)
- Cold start penalty (15s is annoying in dev, problematic in prod)

**Verdict:** Milvus excels at bulk ingestion but struggles with reliability and developer experience. For general-purpose vector search, **Qdrant or Elasticsearch are safer choices**. Use Milvus only if you need maximum write throughput and have expertise to handle its quirks.

### Learnings: ⭐⭐⭐⭐ (4/5)
**What did I learn?**

1. **Raw speed ≠ production readiness** - Milvus is fastest but least reliable under load
2. **Integer IDs are a tax** - Hashing compound keys adds complexity vs string IDs
3. **Dependency management matters** - marshmallow conflict wasted significant time
4. **Cold start is a real cost** - 15s delay impacts dev velocity and UX
5. **Maturity shows** - Qdrant/Elasticsearch have smoother APIs from years of refinement

**Why 4/5?** Learned important lessons about performance trade-offs and that "fastest" doesn't mean "best."

### Fun: ⭐⭐ (2/5)
**Was this enjoyable?**

**No.** Milvus was the **least fun** database to implement:

**Frustrations:**
- Spent 30+ minutes debugging marshmallow dependency conflict
- Integer ID requirement forced hashing workaround (all other DBs use strings)
- Stats API showing 0 created confusion and wasted time
- 15-second cold starts are tedious during dev/test cycles
- Noisy logs made debugging harder
- Made more implementation mistakes than any other DB (likely due to less training data)

**Bright Spots:**
- Ingestion speed was genuinely impressive (32K emb/s!)
- When it worked, it worked well

**Verdict:** Milvus feels like a **power user's database** - fast but requiring expertise. Qdrant's "zero-config magic" spoiled me. After the smooth experience with Elasticsearch and Qdrant, Milvus felt like a step backward in developer experience.

## Conclusion

Milvus is a **high-performance specialist** that excels at one thing: ingesting vectors at blazing speed (32,496 emb/s). However, this speed comes with significant trade-offs:

- **High learning curve** (integer IDs, dependency conflicts, confusing APIs)
- **Poor concurrency** (90% success rate vs 96-100% for others)
- **Cold start penalty** (15 seconds vs instant for others)
- **Rough developer experience** (noisy logs, stats lag, multiple gotchas)

**Final Recommendation:** Use Milvus if you need **maximum write throughput** and have **expertise to handle its complexity**. For most use cases, **Qdrant or Elasticsearch offer better balance** of performance, reliability, and developer experience.

**Rankings So Far:**
1. **Qdrant** - Best all-around (speed + reliability + DX)
2. **Elasticsearch** - Rock-solid reliability, great hybrid search
3. **Postgres** - Excellent DX, good reliability, slower but acceptable
4. **Milvus** - Fastest ingestion, but poor reliability + high learning curve
5. **Redis** - Fast but unreliable (55% success rate disqualifies it)