#!/usr/bin/env python3
"""
Storage analysis script for vector database disk usage.

Measures disk space consumed by:
- Vector embeddings and indexes
- Metadata storage
- Database overhead
- Total storage footprint
"""

import subprocess
import json
from typing import Dict, Any
from pathlib import Path


def get_directory_size(path: Path) -> int:
    """Get total size of a directory in bytes."""
    if not path.exists():
        return 0

    try:
        result = subprocess.run(
            ["du", "-sb", str(path)],
            capture_output=True,
            text=True,
            check=True
        )
        size_bytes = int(result.stdout.split()[0])
        return size_bytes
    except Exception as e:
        print(f"Error measuring {path}: {e}")
        return 0


def get_docker_volume_size(volume_name: str) -> Dict[str, Any]:
    """Get size of a Docker volume."""
    try:
        # Get volume mount point
        result = subprocess.run(
            ["docker", "volume", "inspect", volume_name],
            capture_output=True,
            text=True,
            check=True
        )
        volume_info = json.loads(result.stdout)[0]
        mountpoint = volume_info.get("Mountpoint", "")

        if mountpoint:
            # Measure size (requires sudo on some systems)
            try:
                result = subprocess.run(
                    ["du", "-sb", mountpoint],
                    capture_output=True,
                    text=True,
                    check=True
                )
                size_bytes = int(result.stdout.split()[0])
                return {
                    "volume": volume_name,
                    "mountpoint": mountpoint,
                    "size_bytes": size_bytes,
                    "size_mb": size_bytes / (1024 * 1024),
                    "size_gb": size_bytes / (1024 * 1024 * 1024)
                }
            except subprocess.CalledProcessError:
                # If du fails (permission issues), try alternative
                return {
                    "volume": volume_name,
                    "mountpoint": mountpoint,
                    "error": "Permission denied - run with sudo for accurate measurements"
                }
        else:
            return {
                "volume": volume_name,
                "error": "Mountpoint not found"
            }
    except Exception as e:
        return {
            "volume": volume_name,
            "error": str(e)
        }


def get_postgres_database_size() -> Dict[str, Any]:
    """Get PostgreSQL database size using psql."""
    try:
        # Connect to database and get size
        result = subprocess.run(
            [
                "docker", "exec", "postgres",
                "psql", "-U", "postgres", "-d", "vectors",
                "-t", "-A", "-c",
                "SELECT pg_database_size('vectors');"
            ],
            capture_output=True,
            text=True,
            check=True
        )

        size_bytes = int(result.stdout.strip())

        # Get table and index sizes
        table_info = subprocess.run(
            [
                "docker", "exec", "postgres",
                "psql", "-U", "postgres", "-d", "vectors",
                "-t", "-A", "-c",
                """
                SELECT
                    pg_size_pretty(pg_total_relation_size('knitting_patterns')) as total_size,
                    pg_size_pretty(pg_relation_size('knitting_patterns')) as table_size,
                    pg_size_pretty(pg_total_relation_size('knitting_patterns') - pg_relation_size('knitting_patterns')) as index_size;
                """
            ],
            capture_output=True,
            text=True,
            check=True
        )

        sizes = table_info.stdout.strip().split('|')

        return {
            "database": "postgres",
            "total_size_bytes": size_bytes,
            "total_size_mb": size_bytes / (1024 * 1024),
            "total_size_gb": size_bytes / (1024 * 1024 * 1024),
            "table_size": sizes[1] if len(sizes) > 1 else "unknown",
            "index_size": sizes[2] if len(sizes) > 2 else "unknown"
        }
    except Exception as e:
        return {
            "database": "postgres",
            "error": str(e)
        }


def analyze_embeddings_cache() -> Dict[str, Any]:
    """Analyze the embeddings cache directory."""
    embeddings_dir = Path("./embeddings")

    if not embeddings_dir.exists():
        return {
            "directory": str(embeddings_dir),
            "error": "Embeddings directory not found"
        }

    total_size = get_directory_size(embeddings_dir)

    # Count files
    npy_files = list(embeddings_dir.glob("**/*.npy"))
    json_files = list(embeddings_dir.glob("**/*.json"))

    return {
        "directory": str(embeddings_dir),
        "total_size_bytes": total_size,
        "total_size_mb": total_size / (1024 * 1024),
        "total_size_gb": total_size / (1024 * 1024 * 1024),
        "num_npy_files": len(npy_files),
        "num_json_files": len(json_files),
        "total_files": len(npy_files) + len(json_files)
    }


def analyze_storage() -> Dict[str, Any]:
    """Run complete storage analysis."""
    print("Vector Database Storage Analysis")
    print("=" * 60)

    results = {}

    # Analyze embeddings cache
    print("\n1. Embeddings Cache")
    print("-" * 60)
    embeddings = analyze_embeddings_cache()
    results["embeddings_cache"] = embeddings

    if "error" not in embeddings:
        print(f"  Directory: {embeddings['directory']}")
        print(f"  Total size: {embeddings['total_size_mb']:.2f} MB ({embeddings['total_size_gb']:.3f} GB)")
        print(f"  Files: {embeddings['num_npy_files']} .npy, {embeddings['num_json_files']} .json")
    else:
        print(f"  Error: {embeddings['error']}")

    # Analyze PostgreSQL database
    print("\n2. PostgreSQL Database")
    print("-" * 60)
    postgres = get_postgres_database_size()
    results["postgres"] = postgres

    if "error" not in postgres:
        print(f"  Total size: {postgres['total_size_mb']:.2f} MB ({postgres['total_size_gb']:.3f} GB)")
        print(f"  Table size: {postgres['table_size']}")
        print(f"  Index size: {postgres['index_size']}")
    else:
        print(f"  Error: {postgres['error']}")

    # Analyze Docker volumes
    print("\n3. Docker Volumes")
    print("-" * 60)

    volumes = [
        "vectordatabaseexperimentation_postgres_data",
        "vectordatabaseexperimentation_colpali_cache"
    ]

    volume_results = []
    for volume in volumes:
        vol_info = get_docker_volume_size(volume)
        volume_results.append(vol_info)

        if "error" not in vol_info:
            print(f"  {volume}:")
            print(f"    Size: {vol_info['size_mb']:.2f} MB ({vol_info['size_gb']:.3f} GB)")
        else:
            print(f"  {volume}: {vol_info['error']}")

    results["docker_volumes"] = volume_results

    # Calculate totals
    print("\n4. Summary")
    print("-" * 60)

    total_storage = 0
    if "error" not in embeddings:
        total_storage += embeddings["total_size_bytes"]

    if "error" not in postgres:
        total_storage += postgres["total_size_bytes"]

    for vol in volume_results:
        if "error" not in vol:
            total_storage += vol["size_bytes"]

    summary = {
        "total_storage_bytes": total_storage,
        "total_storage_mb": total_storage / (1024 * 1024),
        "total_storage_gb": total_storage / (1024 * 1024 * 1024)
    }

    results["summary"] = summary

    print(f"  Total storage: {summary['total_storage_mb']:.2f} MB ({summary['total_storage_gb']:.3f} GB)")

    # Storage per pattern
    if "error" not in embeddings and embeddings["num_npy_files"] > 0:
        storage_per_pattern = embeddings["total_size_mb"] / embeddings["num_npy_files"]
        print(f"  Avg per pattern: {storage_per_pattern:.2f} MB")
        results["summary"]["avg_storage_per_pattern_mb"] = storage_per_pattern

    return results


def main():
    """Run storage analysis and save results."""
    results = analyze_storage()

    # Save to JSON
    output_file = "storage_analysis_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Results saved to: {output_file}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()