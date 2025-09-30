#!/usr/bin/env python3
"""
Benchmark search performance for vector databases.

Measures query latency percentiles (p50, p95, p99) across 20 realistic knitting pattern queries.
Tests different result sizes (k=5, 10, 20) and cold vs warm cache performance.
"""

import asyncio
import httpx
import time
import statistics
from typing import List, Dict, Any
import json


# 20 realistic knitting pattern search queries
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
    "amigurumi toys",
    "chunky knit blanket",
    "fingerless gloves",
    "cardigan patterns",
    "fair isle yoke",
    "easy beginner patterns",
    "lace weight shawl",
    "worsted weight sweater",
    "circular knitting patterns",
    "textured stitch patterns"
]

# Result sizes to test
K_VALUES = [5, 10, 20]


async def measure_search_latency(
    client: httpx.AsyncClient,
    query: str,
    k: int = 10
) -> Dict[str, Any]:
    """Execute a single search query and measure latency."""
    start = time.perf_counter()

    try:
        response = await client.post(
            "http://localhost:8000/api/search/text",
            json={"query": query, "k": k},
            timeout=60.0
        )
        latency = time.perf_counter() - start

        if response.status_code == 200:
            data = response.json()
            return {
                "query": query,
                "k": k,
                "latency": latency,
                "num_results": len(data.get("results", [])),
                "success": True
            }
        else:
            return {
                "query": query,
                "k": k,
                "latency": latency,
                "error": f"HTTP {response.status_code}",
                "success": False
            }
    except Exception as e:
        latency = time.perf_counter() - start
        return {
            "query": query,
            "k": k,
            "latency": latency,
            "error": str(e),
            "success": False
        }


async def run_benchmark_round(
    queries: List[str],
    k: int,
    round_name: str
) -> Dict[str, Any]:
    """Run a complete benchmark round with all queries."""
    print(f"\n{'='*60}")
    print(f"Running {round_name} (k={k})")
    print(f"{'='*60}")

    results = []
    latencies = []

    async with httpx.AsyncClient() as client:
        for i, query in enumerate(queries, 1):
            result = await measure_search_latency(client, query, k)
            results.append(result)

            if result["success"]:
                latencies.append(result["latency"])
                print(f"  [{i:2d}/20] {query:35s} {result['latency']*1000:7.2f}ms")
            else:
                print(f"  [{i:2d}/20] {query:35s} FAILED: {result.get('error', 'Unknown')}")

    # Calculate statistics
    if latencies:
        latencies_sorted = sorted(latencies)
        stats = {
            "round": round_name,
            "k": k,
            "total_queries": len(queries),
            "successful_queries": len(latencies),
            "failed_queries": len(queries) - len(latencies),
            "min_ms": min(latencies) * 1000,
            "max_ms": max(latencies) * 1000,
            "mean_ms": statistics.mean(latencies) * 1000,
            "median_ms": statistics.median(latencies) * 1000,
            "p50_ms": statistics.quantiles(latencies, n=100)[49] * 1000,
            "p95_ms": statistics.quantiles(latencies, n=100)[94] * 1000,
            "p99_ms": statistics.quantiles(latencies, n=100)[98] * 1000,
            "stdev_ms": statistics.stdev(latencies) * 1000 if len(latencies) > 1 else 0,
        }
    else:
        stats = {
            "round": round_name,
            "k": k,
            "total_queries": len(queries),
            "successful_queries": 0,
            "failed_queries": len(queries),
            "error": "All queries failed"
        }

    return {"stats": stats, "results": results}


def print_summary(all_rounds: List[Dict[str, Any]]):
    """Print summary table of all benchmark rounds."""
    print(f"\n{'='*60}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*60}")
    print(f"{'Round':<20s} {'k':>3s} {'Success':>7s} {'p50':>8s} {'p95':>8s} {'p99':>8s}")
    print(f"{'-'*60}")

    for round_data in all_rounds:
        stats = round_data["stats"]
        if "error" not in stats:
            print(
                f"{stats['round']:<20s} "
                f"{stats['k']:>3d} "
                f"{stats['successful_queries']:>3d}/{stats['total_queries']:<3d} "
                f"{stats['p50_ms']:>7.2f}ms "
                f"{stats['p95_ms']:>7.2f}ms "
                f"{stats['p99_ms']:>7.2f}ms"
            )
        else:
            print(f"{stats['round']:<20s} {stats['k']:>3d} FAILED")

    print(f"{'='*60}\n")


async def main():
    """Run complete benchmark suite."""
    print("\nVector Database Search Benchmark")
    print("Testing query latency with 20 realistic knitting pattern searches")

    all_rounds = []

    # Test cold cache (first run)
    for k in K_VALUES:
        round_data = await run_benchmark_round(QUERIES, k, f"Cold Cache (k={k})")
        all_rounds.append(round_data)
        await asyncio.sleep(2)  # Brief pause between rounds

    # Test warm cache (second run)
    for k in K_VALUES:
        round_data = await run_benchmark_round(QUERIES, k, f"Warm Cache (k={k})")
        all_rounds.append(round_data)
        await asyncio.sleep(2)

    # Print summary
    print_summary(all_rounds)

    # Save detailed results
    output_file = "benchmark_results.json"
    with open(output_file, "w") as f:
        json.dump(all_rounds, f, indent=2)

    print(f"Detailed results saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())