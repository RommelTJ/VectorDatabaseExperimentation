# Running Performance Benchmarks

This guide covers how to run the performance evaluation scripts for the vector database implementations.

## Prerequisites

- Docker containers must be running: `docker-compose up -d`
- Database must be populated with training data (80 PDFs)
- Backend API must be accessible at `http://localhost:8000`

## Docker Commands

### 1. Benchmark Search (Query Latency)

Measures p50, p95, p99 latency for 20 realistic queries across different result sizes (k=5, 10, 20) and cold/warm cache scenarios.

```bash
docker exec -it vectordatabaseexperimentation-backend-1 python scripts/benchmark_search.py
```

**Output**: `benchmark_results.json` with detailed latency statistics

---

### 2. Load Test (Concurrent Users)

Simulates 2, 5, and 10 concurrent users making multiple searches to measure throughput and latency under load.

```bash
docker exec -it vectordatabaseexperimentation-backend-1 python scripts/load_test.py
```

**Output**: `load_test_results.json` with QPS and latency under concurrency

---

### 3. Memory Monitor (RAM Usage)

Tracks memory consumption during sequential queries and under concurrent load with 100ms sampling intervals.

```bash
docker exec -it vectordatabaseexperimentation-backend-1 python scripts/memory_monitor.py
```

**Output**: `memory_monitoring_results.json` with peak/mean/delta memory stats

**Note**: For accurate Docker container memory stats, install the `docker` Python package:
```bash
docker exec -it vectordatabaseexperimentation-backend-1 pip install docker
```

---

---

## Storage Analysis (Manual)

Check Docker volume sizes to compare storage overhead between databases:

```bash
# View all volume sizes
docker system df -v

# Or check specific volumes
docker volume ls
```

**Note**: Embeddings size is constant (~217MB), but index overhead and metadata storage varies by database.

---

## Running All Benchmarks

To run the complete benchmark suite sequentially:

```bash
# Run all performance tests
docker exec -it vectordatabaseexperimentation-backend-1 python scripts/benchmark_search.py && \
docker exec -it vectordatabaseexperimentation-backend-1 python scripts/load_test.py && \
docker exec -it vectordatabaseexperimentation-backend-1 python scripts/memory_monitor.py

# View results (they're saved in the container's /app directory)
docker exec -it vectordatabaseexperimentation-backend-1 ls -lh /app/*.json 2>/dev/null || echo "No results found yet"
```

---

## Viewing Results

All scripts output JSON files to the backend container's `/app` directory. To view results:

```bash
# List result files
docker exec vectordatabaseexperimentation-backend-1 sh -c 'ls -lh /app/*_results.json'

# View specific result file
docker exec vectordatabaseexperimentation-backend-1 cat /app/benchmark_results.json | jq .

# Copy results to host
docker cp vectordatabaseexperimentation-backend-1:/app/benchmark_results.json ./
docker cp vectordatabaseexperimentation-backend-1:/app/load_test_results.json ./
docker cp vectordatabaseexperimentation-backend-1:/app/memory_monitoring_results.json ./
```

---

## Interpreting Results

### Benchmark Search
- **p50 latency**: Median query response time (typical user experience)
- **p95 latency**: 95th percentile (slower queries, important for SLAs)
- **p99 latency**: 99th percentile (worst-case scenarios)
- **Cold vs Warm**: First query vs repeated queries (cache effectiveness)

### Load Test
- **QPS (Queries/sec)**: System throughput under concurrent load
- **Latency degradation**: How response times increase with concurrency
- **Failed requests**: System stability under load

### Memory Monitor
- **Peak usage**: Maximum RAM during operations
- **Mean usage**: Average RAM consumption
- **Delta**: Memory increase during query workload

---

## Customizing Benchmarks

### Adjust Query Count
```bash
# Edit NUM_QUERIES in the script, then run
docker exec -it vectordatabaseexperimentation-backend-1 python scripts/benchmark_search.py
```

### Change Concurrency Levels
```bash
# Edit CONCURRENCY_LEVELS in load_test.py
docker exec -it vectordatabaseexperimentation-backend-1 python scripts/load_test.py
```

### Modify Memory Sampling Interval
```bash
# Edit interval_ms parameter (default 100ms)
docker exec -it vectordatabaseexperimentation-backend-1 python scripts/memory_monitor.py
```

---

## Troubleshooting

### "Connection refused" errors
- Ensure backend container is running: `docker ps | grep backend`
- Check API is accessible: `curl http://localhost:8000/api/health`

### Memory monitoring shows system stats instead of container stats
- Install docker package: `docker exec -it vectordatabaseexperimentation-backend-1 pip install docker`
- Or accept system-wide stats (less accurate but functional)

### Scripts not found
- Verify you're in the project root directory
- Check scripts exist: `docker exec -it vectordatabaseexperimentation-backend-1 ls -l scripts/`