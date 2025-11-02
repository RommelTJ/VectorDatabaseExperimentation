# MongoDB Atlas Local - Vector Database Evaluation

**Date**: November 2, 2025
**Version**: MongoDB 8.2.1 (Atlas Local)
**Dataset**: 80 knitting pattern PDFs, 423,741 embeddings (128 dimensions, ColPali)

## Setup and Implementation

### Installation
- **Image**: `mongodb/mongodb-atlas-local:latest`
- **Driver**: motor 3.6.0 (async Python driver for MongoDB)
- **Setup time**: ~15 minutes (including troubleshooting index creation)

### Implementation Complexity
MongoDB Atlas Local's vector search implementation revealed some unexpected quirks:

1. **Index Creation Timing**: The vector search index must be created **after** data insertion, not before. Creating the index on an empty collection and then bulk inserting data causes the index to fail or disappear.

2. **Index Build Delay**: After creating the index, it enters a "BUILDING" state and requires time to index all vectors before becoming "READY" and queryable.

3. **Authentication**: Requires proper authentication setup (`authSource=admin`) for client connections.

### Pain Points
- **Index Creation Order**: Unlike other databases, MongoDB requires index creation after data ingestion. This is counterintuitive and caused significant debugging time.
- **Index Status**: No clear indication of when the index will be ready after creation. Required manual polling of `$listSearchIndexes` to check status.
- **Documentation Gap**: The specific requirements for MongoDB Atlas Local's vector search are not well documented for programmatic usage.

## Performance Metrics

### Ingestion Performance
```
Total embeddings: 423,741
Total time: 10.98 seconds
Average speed: 38,596.9 embeddings/sec
```

**Result**: 🏆 **FASTEST DATABASE TESTED**

Comparison with other databases:
- **1.19x faster** than Milvus (32,496 emb/s - previously fastest)
- **1.68x faster** than Qdrant (22,954 emb/s)
- **27.9x faster** than Postgres (1,385 emb/s)
- **7.1x faster** than Redis (5,450 emb/s)
- **7.5x faster** than Elasticsearch (5,117 emb/s)
- **47.6x faster** than Weaviate (811 emb/s)

### Query Latency (Single User)
```
Cold Cache (k=5):  p50=1,213ms  p95=1,568ms  p99=1,583ms
Warm Cache (k=5):  p50=761ms    p95=1,264ms  p99=1,331ms
Warm Cache (k=10): p50=888ms    p95=1,164ms  p99=1,175ms
```

**Analysis**: Competitive single-user performance. Most latency is ColPali embedding generation (~600-700ms), with actual MongoDB vector search contributing <200ms.

### Concurrency Performance
```
2 users:  100% success (20/20)  | p50=3,006ms  p95=3,878ms
5 users:  100% success (50/50)  | p50=7,235ms  p95=7,711ms
10 users: 100% success (100/100)| p50=19,572ms p95=22,289ms
```

**Results**:
- ✅ **Perfect reliability**: 100% success rate across all concurrency levels
- ⚠️ **Severe latency degradation**: 6.5x slower at 10 users vs single user
- ⚠️ **Poor scalability**: Throughput drops from 0.67 qps (5 users) to 0.50 qps (10 users)

**Comparison**:
- **Reliability**: Tied with Elasticsearch and Weaviate (100% success)
- **Scalability**: Worst performer under load among reliable databases

### Memory Usage
```
Peak usage: 14.2 GB (90.3% of 16GB limit)
Mean usage: 13.9 GB (88.6%)
Memory delta: 384 MB during operations
```

**Analysis**: Memory dominated by ColPali model (~13GB). MongoDB's vector storage adds minimal overhead.

### Storage Overhead
```
Embeddings cache: 207 MB
MongoDB storage: 2.5 GB
Overhead: 12.1x
```

**Result**: 🚨 **LARGEST STORAGE OVERHEAD TESTED**

Comparison:
- **Qdrant**: 360MB (1.66x overhead) - 6.9x more efficient
- **Weaviate**: 641MB (3.1x overhead) - 3.9x more efficient
- **Elasticsearch**: 1.1GB (5.3x overhead) - 2.3x more efficient
- **Redis**: 1.45GB (5.7x overhead) - 1.7x more efficient
- **Postgres**: 1.58GB (6.3x overhead) - 1.6x more efficient
- **MongoDB**: 2.5GB (12.1x overhead) - WORST

**Why so large?**: MongoDB stores vectors as BSON arrays with full document structure, replica set metadata, and journal files. The vector search index itself also contributes significant overhead.

## Key Findings

### Strengths
1. **Blazing Fast Ingestion**: 38.6K emb/s crushes all competitors. Native BSON array storage and efficient bulk operations make it unbeatable for write-heavy workloads.

2. **Perfect Reliability**: 100% success rate even at 10 concurrent users. No dropped queries or errors.

3. **Native Array Storage**: MongoDB stores vector embeddings as native BSON arrays, making the implementation simple and natural.

4. **Familiar API**: If you already know MongoDB, the aggregation pipeline syntax feels natural. Vector search integrates seamlessly into existing queries.

### Weaknesses
1. **Catastrophic Concurrency Performance**: Latency increases 6.5x from single user to 10 users. This is unacceptable for production workloads with any concurrency.

2. **Massive Storage Overhead**: 12.1x overhead is brutal. For large vector datasets, you'll need 12x the storage compared to raw embeddings.

3. **Index Creation Quirk**: The requirement to create indexes AFTER data insertion is counterintuitive and error-prone.

4. **Poor Documentation**: MongoDB Atlas Local's vector search documentation is sparse, especially for programmatic usage and index lifecycle management.

### Unique Observations
- **Index Lifecycle**: MongoDB's async index building means you must poll for "READY" status before querying. This adds complexity to deployment automation.

- **Aggregation Pipeline**: Using `$vectorSearch` in aggregation pipelines is elegant but has a learning curve. The pipeline approach is powerful for combining vector search with other operations.

- **Memory Efficiency**: Despite massive storage overhead, runtime memory usage is reasonable (comparable to other databases).

## Ratings

### Practicality: ⭐⭐ (2/5)
**Would NOT use again for vector search.**

While the blazing fast ingestion is impressive, the combination of catastrophic concurrency performance, massive storage overhead, and quirky index management makes MongoDB unsuitable for production vector search workloads.

**Use only if**:
- You need maximum write throughput AND
- You have zero concurrent reads AND
- Storage cost is not a concern AND
- You're already running MongoDB for other data

**Better alternatives**: Qdrant (balanced), Weaviate (read-optimized), Elasticsearch (hybrid search)

### Learnings: ⭐⭐⭐⭐⭐ (5/5)
**Extremely valuable lessons learned.**

1. **Write Speed ≠ Production Ready**: MongoDB proves that raw ingestion speed doesn't matter if concurrent read performance is terrible.

2. **Storage Efficiency Matters**: At 12.1x overhead, a 1TB vector dataset becomes 12TB. This has real cost implications for cloud deployments.

3. **Index Lifecycle Complexity**: The async, post-insertion index creation pattern is a unique challenge that affects deployment automation.

4. **Trade-off Visibility**: MongoDB's performance characteristics make the read/write trade-offs crystal clear. You can optimize for one or the other, but not both.

### Fun: ⭐⭐ (2/5)
**Frustrating experience overall.**

The positives:
- Initial setup was straightforward
- Seeing 38K emb/s ingestion was thrilling
- Aggregation pipeline syntax is elegant

The negatives:
- Hours lost debugging the index creation timing issue
- Watching latency explode under load was disappointing
- The massive storage overhead feels wasteful
- Constant manual index status polling during testing

**Least fun aspects**: The index creation quirk consumed too much debugging time, and the poor concurrency performance was demoralizing after seeing such impressive ingestion speeds.

## Comparison with Other Databases

### Best at Ingestion Speed
```
1. MongoDB:       38,596 emb/s  ⭐⭐⭐⭐⭐
2. Milvus:        32,496 emb/s  ⭐⭐⭐⭐⭐
3. Qdrant:        22,954 emb/s  ⭐⭐⭐⭐
4. Elasticsearch:  5,117 emb/s  ⭐⭐
5. Redis:          5,450 emb/s  ⭐⭐
6. Postgres:       1,385 emb/s  ⭐
7. Weaviate:         811 emb/s  ⭐
```

### Best at Query Latency (Single User)
```
1. Weaviate:        560ms  ⭐⭐⭐⭐⭐
2. Milvus:          700ms  ⭐⭐⭐⭐
3. MongoDB:         761ms  ⭐⭐⭐⭐
4. Postgres:      1,156ms  ⭐⭐⭐
5. Redis:         1,165ms  ⭐⭐⭐
6. Elasticsearch: 1,150ms  ⭐⭐⭐
7. Qdrant:        1,190ms  ⭐⭐⭐
```

### Best at Concurrency (10 users)
```
1. Elasticsearch: 100% success, 1,150ms p50   ⭐⭐⭐⭐⭐
2. Weaviate:      100% success, ~560ms p50    ⭐⭐⭐⭐⭐
3. Qdrant:         96% success, 1,190ms p50   ⭐⭐⭐⭐
4. Milvus:         90% success, 700ms p50     ⭐⭐⭐
5. MongoDB:       100% success, 19,572ms p50  ⭐
6. Redis:          55% success, 1,165ms p50   ⭐
7. Postgres:      100% success, 1,156ms p50   ⭐⭐⭐⭐
```

### Best Storage Efficiency
```
1. Qdrant:        360MB  (1.66x)  ⭐⭐⭐⭐⭐
2. Weaviate:      641MB  (3.1x)   ⭐⭐⭐⭐
3. Elasticsearch: 1.1GB  (5.3x)   ⭐⭐⭐
4. Redis:         1.45GB (5.7x)   ⭐⭐⭐
5. Postgres:      1.58GB (6.3x)   ⭐⭐⭐
6. Milvus:        [data not available]
7. MongoDB:       2.5GB  (12.1x)  ⭐
```

## Recommendations

### DO Use MongoDB If:
- ✅ You have a write-once, read-rarely pattern
- ✅ You need maximum bulk ingestion speed
- ✅ You have zero concurrent users
- ✅ Storage cost is irrelevant
- ✅ You're already running MongoDB for other data

### DON'T Use MongoDB If:
- ❌ You have any concurrent read workload
- ❌ Query latency matters under load
- ❌ Storage efficiency is a concern
- ❌ You need predictable performance
- ❌ This is a production vector search application

### Better Alternatives:
- **General Purpose**: Qdrant (balanced performance, efficient storage)
- **Read-Heavy**: Weaviate (fastest queries, perfect reliability)
- **Hybrid Search**: Elasticsearch (vector + full-text + filters)
- **Budget**: Postgres (cheapest infrastructure, good enough performance)

## Final Verdict

MongoDB Atlas Local is a **specialist database that excels at bulk writes but fails at concurrent reads**. The 38.6K emb/s ingestion speed is undeniably impressive, but it comes at the cost of:
- 6.5x latency increase under load
- 12.1x storage overhead
- Quirky index management

**Use MongoDB for vector search only as a tactical write buffer** - bulk insert vectors at incredible speed, then sync them to a proper vector database (Qdrant/Weaviate) for actual querying. Don't use it as a standalone production vector search solution.

**Overall Score**: ⭐⭐ (2/5) - Impressive in one dimension, disappointing in everything else.