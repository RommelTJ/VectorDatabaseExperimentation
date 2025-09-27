#!/usr/bin/env python3
"""Quick script to verify the embeddings format"""

import os
import json
import pickle
import torch
from pathlib import Path

def verify_embeddings():
    # Use Docker path when in container
    if os.path.exists('/app/data'):
        embeddings_dir = Path('/app/data/embeddings')
    else:
        embeddings_dir = Path('data/embeddings')

    # Check all files
    files = list(embeddings_dir.glob('*_embeddings.pkl'))
    metadata_files = list(embeddings_dir.glob('*_metadata.json'))

    print(f"Found {len(files)} embedding files")
    print(f"Found {len(metadata_files)} metadata files\n")

    # Check file sizes
    total_size = 0
    for pkl_file in files:
        size_mb = os.path.getsize(pkl_file) / (1024 * 1024)
        total_size += size_mb
        pdf_name = pkl_file.stem.replace('_embeddings', '')
        print(f"{pdf_name}: {size_mb:.2f} MB")

    print(f"\nTotal embeddings size: {total_size:.2f} MB")

    # Load and verify actual tensor data
    print("\n" + "="*60)
    print("Verifying tensor data...")

    # Load one embedding to check torch tensor structure
    test_pkl = files[0] if files else None
    if test_pkl:
        with open(test_pkl, 'rb') as f:
            test_embeddings = pickle.load(f)

        print(f"\nLoaded {test_pkl.stem}:")
        print(f"  Type: {type(test_embeddings)}")
        print(f"  Number of pages: {len(test_embeddings)}")

        if len(test_embeddings) > 0:
            first_page = test_embeddings[0]
            print(f"\nFirst page tensor:")
            print(f"  Type: {type(first_page)}")
            print(f"  Shape: {first_page.shape}")
            print(f"  Dtype: {first_page.dtype}")
            print(f"  Device: {first_page.device}")
            print(f"  Min value: {first_page.min():.4f}")
            print(f"  Max value: {first_page.max():.4f}")
            print(f"  Mean value: {first_page.mean():.4f}")

    # Analyze metadata
    print("\n" + "="*60)
    total_pages = 0
    total_patches = 0

    for json_file in metadata_files:
        with open(json_file, 'r') as f:
            metadata = json.load(f)

        pdf_name = metadata['metadata']['pdf_name']
        page_count = metadata['metadata']['page_count']
        total_pages += page_count

        # Count patches
        pdf_patches = sum(page['num_patches'] for page in metadata['metadata']['pages'])
        total_patches += pdf_patches

        # Check consistency
        all_dims_same = all(page['embedding_dim'] == 128 for page in metadata['metadata']['pages'])
        all_patches_same = all(page['num_patches'] == 1031 for page in metadata['metadata']['pages'])

        print(f"\n{pdf_name}:")
        print(f"  Pages: {page_count}")
        print(f"  Total patches: {pdf_patches:,}")
        print(f"  Patches per page: {metadata['metadata']['pages'][0]['num_patches']}")
        print(f"  Embedding dimension: {metadata['metadata']['pages'][0]['embedding_dim']}")
        print(f"  All dims = 128? {all_dims_same}")
        print(f"  All patches = 1031? {all_patches_same}")

    # Check stats
    stats_path = embeddings_dir / 'ingestion_stats.json'
    with open(stats_path, 'r') as f:
        stats = json.load(f)

    print(f"\nIngestion Statistics:")
    print(f"Total PDFs processed: {stats['processed']}/{stats['total_pdfs']}")
    print(f"Total pages: {stats['total_pages']}")
    print(f"Total patches: {stats['total_patches']:,}")
    print(f"Average patches per page: {stats['total_patches'] / stats['total_pages']:.0f}")
    print(f"Time taken: {stats['total_time_readable']}")
    print(f"Average time per PDF: {stats['average_time_per_pdf']}")

if __name__ == '__main__':
    verify_embeddings()