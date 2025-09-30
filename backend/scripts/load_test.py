#!/usr/bin/env python3
"""
Load testing script for concurrent search performance.

Simulates multiple concurrent users executing searches simultaneously to measure
throughput and latency under load.
"""

import asyncio
import httpx
import time
import statistics
import random
from typing import List, Dict, Any
import json


# Sample queries for load testing
QUERIES = [
    "cable patterns",
    "baby blanket",
    "lace shawl",
    "sock patterns",
    "sweater with raglan sleeves",
    "colorwork mittens",
    "brioche stitch",
    "hat with pompom",
    "scarf with fringe",
    "dishcloth patterns",
]

# Concurrent user levels to test
CONCURRENCY_LEVELS = [2, 5, 10]

# Number of requests per user
REQUESTS_PER_USER = 10


async def user_session(
    client: httpx.AsyncClient,
    user_id: int,
    num_requests: int,
    k: int = 10
) -> List[Dict[str, Any]]:
    """Simulate a single user making multiple search requests."""
    results = []

    for i in range(num_requests):
        query = random.choice(QUERIES)
        start = time.perf_counter()

        try:
            response = await client.post(
                "http://localhost:8000/api/search/text",
                json={"query": query, "k": k},
                timeout=60.0
            )
            latency = time.perf_counter() - start

            result = {
                "user_id": user_id,
                "request_num": i + 1,
                "query": query,
                "latency": latency,
                "success": response.status_code == 200,
                "status_code": response.status_code
            }

            if response.status_code == 200:
                data = response.json()
                result["num_results"] = len(data.get("results", []))

        except Exception as e:
            latency = time.perf_counter() - start
            result = {
                "user_id": user_id,
                "request_num": i + 1,
                "query": query,
                "latency": latency,
                "success": False,
                "error": str(e)
            }

        results.append(result)

        # Small random delay between requests (0-500ms)
        await asyncio.sleep(random.uniform(0, 0.5))

    return results


async def run_load_test(
    num_users: int,
    requests_per_user: int,
    k: int = 10
) -> Dict[str, Any]:
    """Run a load test with specified number of concurrent users."""
    print(f"\n{'='*60}")
    print(f"Load Test: {num_users} concurrent users, {requests_per_user} requests each")
    print(f"{'='*60}")

    start_time = time.perf_counter()

    async with httpx.AsyncClient() as client:
        # Launch all user sessions concurrently
        tasks = [
            user_session(client, user_id, requests_per_user, k)
            for user_id in range(1, num_users + 1)
        ]

        all_results = await asyncio.gather(*tasks)

    total_time = time.perf_counter() - start_time

    # Flatten results
    flat_results = [result for user_results in all_results for result in user_results]

    # Calculate statistics
    successful_requests = [r for r in flat_results if r["success"]]
    failed_requests = [r for r in flat_results if not r["success"]]

    latencies = [r["latency"] for r in successful_requests]

    if latencies:
        latencies_sorted = sorted(latencies)
        stats = {
            "num_users": num_users,
            "requests_per_user": requests_per_user,
            "total_requests": len(flat_results),
            "successful_requests": len(successful_requests),
            "failed_requests": len(failed_requests),
            "total_time_s": total_time,
            "throughput_qps": len(successful_requests) / total_time,
            "min_ms": min(latencies) * 1000,
            "max_ms": max(latencies) * 1000,
            "mean_ms": statistics.mean(latencies) * 1000,
            "median_ms": statistics.median(latencies) * 1000,
            "p50_ms": statistics.quantiles(latencies, n=100)[49] * 1000,
            "p95_ms": statistics.quantiles(latencies, n=100)[94] * 1000,
            "p99_ms": statistics.quantiles(latencies, n=100)[98] * 1000,
            "stdev_ms": statistics.stdev(latencies) * 1000 if len(latencies) > 1 else 0,
        }

        print(f"\nResults:")
        print(f"  Total time: {stats['total_time_s']:.2f}s")
        print(f"  Successful: {stats['successful_requests']}/{stats['total_requests']}")
        print(f"  Failed: {stats['failed_requests']}")
        print(f"  Throughput: {stats['throughput_qps']:.2f} queries/sec")
        print(f"  Latency p50: {stats['p50_ms']:.2f}ms")
        print(f"  Latency p95: {stats['p95_ms']:.2f}ms")
        print(f"  Latency p99: {stats['p99_ms']:.2f}ms")

    else:
        stats = {
            "num_users": num_users,
            "requests_per_user": requests_per_user,
            "total_requests": len(flat_results),
            "successful_requests": 0,
            "failed_requests": len(failed_requests),
            "total_time_s": total_time,
            "error": "All requests failed"
        }
        print(f"\nAll requests failed!")

    return {"stats": stats, "results": flat_results}


def print_summary(all_tests: List[Dict[str, Any]]):
    """Print summary table of all load tests."""
    print(f"\n{'='*70}")
    print("LOAD TEST SUMMARY")
    print(f"{'='*70}")
    print(f"{'Users':>5s} {'Requests':>8s} {'Success':>7s} {'Time':>7s} {'QPS':>7s} {'p50':>8s} {'p95':>8s} {'p99':>8s}")
    print(f"{'-'*70}")

    for test_data in all_tests:
        stats = test_data["stats"]
        if "error" not in stats:
            print(
                f"{stats['num_users']:>5d} "
                f"{stats['total_requests']:>8d} "
                f"{stats['successful_requests']:>4d}/{stats['total_requests']:<3d} "
                f"{stats['total_time_s']:>6.2f}s "
                f"{stats['throughput_qps']:>7.2f} "
                f"{stats['p50_ms']:>7.2f}ms "
                f"{stats['p95_ms']:>7.2f}ms "
                f"{stats['p99_ms']:>7.2f}ms"
            )
        else:
            print(f"{stats['num_users']:>5d} {stats['total_requests']:>8d} FAILED")

    print(f"{'='*70}\n")


async def main():
    """Run complete load test suite."""
    print("\nVector Database Load Test")
    print(f"Testing concurrent search performance")

    all_tests = []

    for num_users in CONCURRENCY_LEVELS:
        test_data = await run_load_test(num_users, REQUESTS_PER_USER)
        all_tests.append(test_data)
        await asyncio.sleep(3)  # Cool-down between tests

    # Print summary
    print_summary(all_tests)

    # Save detailed results
    output_file = "load_test_results.json"
    with open(output_file, "w") as f:
        json.dump(all_tests, f, indent=2)

    print(f"Detailed results saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())