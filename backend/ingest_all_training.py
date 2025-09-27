#!/usr/bin/env python3
"""
Full ingestion test script for loading all training PDFs into the database.
This script monitors ingestion time and provides progress updates.
"""

import asyncio
import json
import pickle
import time
from pathlib import Path
import sys
import os

# Add backend directory to path
sys.path.append('/app')

from adapters import get_database_adapter

async def ingest_all_training_data():
    """Load all 80 training PDFs from cache into the database"""

    db_type = os.getenv("VECTOR_DB_TYPE", "postgres")
    print(f"Starting full ingestion test for {db_type}")
    print("=" * 60)

    # Initialize database adapter
    db_adapter = get_database_adapter(db_type)
    await db_adapter.connect()

    # Create collection fresh
    print("Creating fresh collection...")
    await db_adapter.create_collection("patterns", dimension=128)

    # Get all embedding files
    embeddings_dir = Path("/app/data/embeddings")
    embedding_files = sorted(list(embeddings_dir.glob("*_embeddings.pkl")))

    print(f"Found {len(embedding_files)} embedding files to ingest")
    print("=" * 60)

    total_embeddings = 0
    total_pages = 0
    start_time = time.time()

    # Process each PDF
    for idx, emb_file in enumerate(embedding_files, 1):
        pdf_start = time.time()

        # Load embeddings
        with open(emb_file, 'rb') as f:
            embeddings_data = pickle.load(f)

        # Load metadata
        metadata_file = emb_file.parent / emb_file.name.replace('_embeddings.pkl', '_metadata.json')
        with open(metadata_file, 'r') as f:
            metadata_info = json.load(f)

        pdf_name = metadata_info['metadata']['pdf_name']
        pdf_id = pdf_name.replace('.pdf', '')
        page_count = metadata_info['metadata']['page_count']

        print(f"\n[{idx}/{len(embedding_files)}] Processing: {pdf_name}")
        print(f"  Pages: {page_count}")

        pdf_embeddings_count = 0

        # Process each page
        for page_idx, page_info in enumerate(metadata_info['metadata']['pages']):
            page_embeddings = embeddings_data[page_idx]
            num_patches = page_info['num_patches']

            # Prepare metadata for batch insert
            metadata_list = []
            for patch_idx in range(num_patches):
                metadata_list.append({
                    'pdf_id': pdf_id,
                    'page_num': page_idx,
                    'patch_index': patch_idx,
                    'title': pdf_name,
                    'difficulty': 'unknown',
                    'yarn_weight': 'unknown'
                })

            # Convert embeddings to list format
            embeddings_list = page_embeddings.tolist()

            # Insert this page's embeddings
            await db_adapter.insert("patterns", embeddings_list, metadata_list)

            pdf_embeddings_count += len(metadata_list)
            total_pages += 1

        pdf_time = time.time() - pdf_start
        total_embeddings += pdf_embeddings_count

        print(f"  Embeddings: {pdf_embeddings_count}")
        print(f"  Time: {pdf_time:.2f}s")
        print(f"  Speed: {pdf_embeddings_count/pdf_time:.1f} embeddings/sec")

        # Progress report every 10 PDFs
        if idx % 10 == 0:
            elapsed = time.time() - start_time
            print(f"\n--- Progress Report ---")
            print(f"Processed: {idx}/{len(embedding_files)} PDFs")
            print(f"Total embeddings: {total_embeddings}")
            print(f"Elapsed time: {elapsed:.2f}s")
            print(f"Average speed: {total_embeddings/elapsed:.1f} embeddings/sec")
            print(f"Estimated remaining: {((len(embedding_files)-idx)/idx)*elapsed:.1f}s")
            print("-" * 23)

    # Final report
    total_time = time.time() - start_time

    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    print(f"Database: {db_type}")
    print(f"PDFs processed: {len(embedding_files)}")
    print(f"Total pages: {total_pages}")
    print(f"Total embeddings: {total_embeddings}")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Average speed: {total_embeddings/total_time:.1f} embeddings/sec")
    print(f"Average per PDF: {total_time/len(embedding_files):.2f} seconds")

    # Verify count in database
    async with db_adapter.pool.acquire() as conn:
        count_result = await conn.fetchval("SELECT COUNT(*) FROM patterns")
        print(f"\nVerification: {count_result} embeddings in database")

    await db_adapter.disconnect()

    return {
        'pdfs_processed': len(embedding_files),
        'total_embeddings': total_embeddings,
        'total_time': total_time,
        'embeddings_per_second': total_embeddings/total_time
    }

if __name__ == "__main__":
    asyncio.run(ingest_all_training_data())