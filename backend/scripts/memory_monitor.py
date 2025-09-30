#!/usr/bin/env python3
"""
Memory monitoring script for vector database operations.

Tracks RAM usage during search operations and load testing to identify
memory consumption patterns and peak usage.
"""

import asyncio
import httpx
import psutil
import time
import random
from typing import List, Dict, Any
import json
from datetime import datetime


# Sample queries
QUERIES = [
    "cable patterns",
    "baby blanket",
    "lace shawl",
    "sock patterns",
    "sweater with raglan sleeves",
]


def get_container_memory_stats(container_name: str = "backend") -> Dict[str, float]:
    """
    Get memory stats for a Docker container.
    Falls back to system-wide stats if Docker is not available.
    """
    try:
        import docker
        client = docker.from_env()
        container = client.containers.get(container_name)
        stats = container.stats(stream=False)

        memory_stats = stats.get("memory_stats", {})
        usage = memory_stats.get("usage", 0)
        limit = memory_stats.get("limit", 0)

        return {
            "usage_mb": usage / (1024 * 1024),
            "limit_mb": limit / (1024 * 1024),
            "usage_percent": (usage / limit * 100) if limit > 0 else 0,
            "source": "docker"
        }
    except Exception as e:
        # Fall back to system-wide memory stats
        mem = psutil.virtual_memory()
        return {
            "usage_mb": mem.used / (1024 * 1024),
            "limit_mb": mem.total / (1024 * 1024),
            "usage_percent": mem.percent,
            "source": "system",
            "note": f"Docker stats unavailable: {str(e)}"
        }


async def monitor_memory_during_queries(
    num_queries: int = 20,
    interval_ms: int = 100,
    k: int = 10
) -> Dict[str, Any]:
    """
    Monitor memory usage while executing search queries.

    Args:
        num_queries: Number of search queries to execute
        interval_ms: Memory sampling interval in milliseconds
        k: Number of results per query
    """
    print(f"\n{'='*60}")
    print(f"Memory Monitoring During {num_queries} Queries")
    print(f"{'='*60}")

    memory_samples = []
    query_events = []

    # Start memory monitoring task
    monitoring = True

    async def memory_sampler():
        """Background task to sample memory at regular intervals."""
        while monitoring:
            timestamp = time.perf_counter()
            mem_stats = get_container_memory_stats()
            memory_samples.append({
                "timestamp": timestamp,
                "usage_mb": mem_stats["usage_mb"],
                "usage_percent": mem_stats["usage_percent"]
            })
            await asyncio.sleep(interval_ms / 1000.0)

    # Start monitoring
    monitor_task = asyncio.create_task(memory_sampler())
    start_time = time.perf_counter()

    # Execute queries
    async with httpx.AsyncClient() as client:
        for i in range(num_queries):
            query = random.choice(QUERIES)
            query_start = time.perf_counter()

            try:
                response = await client.post(
                    "http://localhost:8000/api/search/text",
                    json={"query": query, "k": k},
                    timeout=60.0
                )
                query_end = time.perf_counter()

                query_events.append({
                    "query_num": i + 1,
                    "query": query,
                    "start_time": query_start,
                    "end_time": query_end,
                    "latency_ms": (query_end - query_start) * 1000,
                    "success": response.status_code == 200
                })

                print(f"  Query {i+1}/{num_queries}: {query} ({(query_end - query_start)*1000:.2f}ms)")

            except Exception as e:
                query_end = time.perf_counter()
                query_events.append({
                    "query_num": i + 1,
                    "query": query,
                    "start_time": query_start,
                    "end_time": query_end,
                    "latency_ms": (query_end - query_start) * 1000,
                    "success": False,
                    "error": str(e)
                })
                print(f"  Query {i+1}/{num_queries}: {query} FAILED")

            await asyncio.sleep(0.5)  # Brief pause between queries

    # Stop monitoring
    monitoring = False
    await monitor_task

    total_time = time.perf_counter() - start_time

    # Analyze memory usage
    if memory_samples:
        usage_values = [s["usage_mb"] for s in memory_samples]
        percent_values = [s["usage_percent"] for s in memory_samples]

        stats = {
            "num_queries": num_queries,
            "total_time_s": total_time,
            "num_samples": len(memory_samples),
            "memory_mb": {
                "min": min(usage_values),
                "max": max(usage_values),
                "mean": sum(usage_values) / len(usage_values),
                "peak": max(usage_values)
            },
            "memory_percent": {
                "min": min(percent_values),
                "max": max(percent_values),
                "mean": sum(percent_values) / len(percent_values),
                "peak": max(percent_values)
            },
            "memory_delta_mb": max(usage_values) - min(usage_values)
        }

        print(f"\nMemory Statistics:")
        print(f"  Samples: {stats['num_samples']}")
        print(f"  Peak usage: {stats['memory_mb']['peak']:.2f} MB ({stats['memory_percent']['peak']:.2f}%)")
        print(f"  Mean usage: {stats['memory_mb']['mean']:.2f} MB ({stats['memory_percent']['mean']:.2f}%)")
        print(f"  Memory delta: {stats['memory_delta_mb']:.2f} MB")

    else:
        stats = {"error": "No memory samples collected"}

    return {
        "stats": stats,
        "memory_samples": memory_samples,
        "query_events": query_events
    }


async def monitor_memory_under_load(
    num_concurrent_users: int = 5,
    requests_per_user: int = 10,
    interval_ms: int = 100
) -> Dict[str, Any]:
    """
    Monitor memory usage during concurrent load testing.

    Args:
        num_concurrent_users: Number of concurrent users
        requests_per_user: Requests per user
        interval_ms: Memory sampling interval in milliseconds
    """
    print(f"\n{'='*60}")
    print(f"Memory Monitoring Under Load ({num_concurrent_users} users)")
    print(f"{'='*60}")

    memory_samples = []
    monitoring = True

    async def memory_sampler():
        """Background task to sample memory at regular intervals."""
        while monitoring:
            timestamp = time.perf_counter()
            mem_stats = get_container_memory_stats()
            memory_samples.append({
                "timestamp": timestamp,
                "usage_mb": mem_stats["usage_mb"],
                "usage_percent": mem_stats["usage_percent"]
            })
            await asyncio.sleep(interval_ms / 1000.0)

    async def user_session(user_id: int):
        """Simulate a single user making multiple requests."""
        async with httpx.AsyncClient() as client:
            for i in range(requests_per_user):
                query = random.choice(QUERIES)
                try:
                    await client.post(
                        "http://localhost:8000/api/search/text",
                        json={"query": query, "k": 10},
                        timeout=60.0
                    )
                except Exception:
                    pass
                await asyncio.sleep(random.uniform(0, 0.5))

    # Start monitoring
    monitor_task = asyncio.create_task(memory_sampler())
    start_time = time.perf_counter()

    # Run concurrent users
    user_tasks = [user_session(i) for i in range(num_concurrent_users)]
    await asyncio.gather(*user_tasks)

    # Stop monitoring
    monitoring = False
    await monitor_task

    total_time = time.perf_counter() - start_time

    # Analyze memory usage
    if memory_samples:
        usage_values = [s["usage_mb"] for s in memory_samples]
        percent_values = [s["usage_percent"] for s in memory_samples]

        stats = {
            "num_concurrent_users": num_concurrent_users,
            "requests_per_user": requests_per_user,
            "total_time_s": total_time,
            "num_samples": len(memory_samples),
            "memory_mb": {
                "min": min(usage_values),
                "max": max(usage_values),
                "mean": sum(usage_values) / len(usage_values),
                "peak": max(usage_values)
            },
            "memory_percent": {
                "min": min(percent_values),
                "max": max(percent_values),
                "mean": sum(percent_values) / len(percent_values),
                "peak": max(percent_values)
            },
            "memory_delta_mb": max(usage_values) - min(usage_values)
        }

        print(f"\nMemory Statistics:")
        print(f"  Samples: {stats['num_samples']}")
        print(f"  Peak usage: {stats['memory_mb']['peak']:.2f} MB ({stats['memory_percent']['peak']:.2f}%)")
        print(f"  Mean usage: {stats['memory_mb']['mean']:.2f} MB ({stats['memory_percent']['mean']:.2f}%)")
        print(f"  Memory delta: {stats['memory_delta_mb']:.2f} MB")

    else:
        stats = {"error": "No memory samples collected"}

    return {
        "stats": stats,
        "memory_samples": memory_samples
    }


async def main():
    """Run complete memory monitoring suite."""
    print("\nVector Database Memory Monitoring")
    print(f"Timestamp: {datetime.now().isoformat()}")

    results = {}

    # Test 1: Sequential queries
    results["sequential_queries"] = await monitor_memory_during_queries(
        num_queries=20,
        interval_ms=100
    )
    await asyncio.sleep(3)

    # Test 2: Load test with 5 concurrent users
    results["concurrent_load"] = await monitor_memory_under_load(
        num_concurrent_users=5,
        requests_per_user=10,
        interval_ms=100
    )

    # Save results
    output_file = "memory_monitoring_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Results saved to: {output_file}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())