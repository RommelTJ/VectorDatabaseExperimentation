#!/usr/bin/env python3
"""
Offline ingestion script for pre-embedding training PDFs using ColPali.
Processes all PDFs in the training set and saves embeddings to disk.
"""

import os
import json
import pickle
import torch
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import time
import logging
from pdf2image import convert_from_bytes
from PIL import Image

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the ColPali model (adjusted for running inside backend directory)
from colpali_model import ColPaliModel
from pdf_processor import PDFProcessor


def read_training_data() -> List[str]:
    """Read the list of training PDFs from TrainingData.md"""
    # Find TrainingData.md (Docker or local)
    if os.path.exists('/app/data/TrainingData.md'):
        training_data_path = '/app/data/TrainingData.md'
    else:
        training_data_path = '../data/TrainingData.md'

    training_files = []
    with open(training_data_path, 'r') as f:
        in_training_section = False
        for line in f:
            if '## Training Set (80 PDFs)' in line:
                in_training_section = True
                continue
            if in_training_section and line.strip():
                # Match lines like "1. filename.pdf"
                if line.strip()[0].isdigit() and '. ' in line:
                    filename = line.strip().split('. ', 1)[1]
                    training_files.append(filename)
    return training_files


def process_pdf(pdf_path: Path, model: ColPaliModel, processor: PDFProcessor) -> Dict[str, Any]:
    """Process a single PDF and generate embeddings."""
    logger.info(f"Processing: {pdf_path.name}")

    # Read PDF bytes
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()

    # Convert PDF to images
    images = processor.pdf_to_images(pdf_bytes)
    logger.info(f"  Converted to {len(images)} images")

    # Generate embeddings for each page
    page_embeddings = []
    for i, image in enumerate(images):
        logger.info(f"  Embedding page {i+1}/{len(images)}")

        # ColPali expects a list of images
        embeddings = model.embed_images([image])

        # Store embeddings for this page
        # ColPali returns shape [batch, num_patches, embed_dim]
        # For single image: [1, num_patches, embed_dim]
        page_embedding = embeddings[0].cpu()  # Remove batch dimension
        page_embeddings.append(page_embedding)

    # Create metadata
    metadata = {
        'pdf_name': pdf_path.name,
        'pdf_path': str(pdf_path),
        'page_count': len(images),
        'pages': []
    }

    for i, (image, embedding) in enumerate(zip(images, page_embeddings)):
        page_info = {
            'page_number': i + 1,
            'width': image.width,
            'height': image.height,
            'embedding_shape': list(embedding.shape),
            'num_patches': embedding.shape[0],
            'embedding_dim': embedding.shape[1]
        }
        metadata['pages'].append(page_info)

    result = {
        'metadata': metadata,
        'embeddings': page_embeddings,  # List of tensors, one per page
        'processed_at': datetime.now().isoformat()
    }

    return result


def save_embeddings(pdf_name: str, data: Dict[str, Any], output_dir: Path):
    """Save embeddings and metadata to disk."""
    # Create clean filename (remove special chars)
    safe_name = pdf_name.replace('.pdf', '').replace(' ', '_')

    # Save embeddings as pickle (preserves tensor format)
    embeddings_file = output_dir / f"{safe_name}_embeddings.pkl"
    with open(embeddings_file, 'wb') as f:
        pickle.dump(data['embeddings'], f)

    # Save metadata as JSON
    metadata_file = output_dir / f"{safe_name}_metadata.json"
    # Remove embeddings from dict before saving as JSON
    metadata_dict = {
        'metadata': data['metadata'],
        'processed_at': data['processed_at'],
        'embeddings_file': str(embeddings_file.name)
    }
    with open(metadata_file, 'w') as f:
        json.dump(metadata_dict, f, indent=2)

    logger.info(f"  Saved embeddings to {embeddings_file.name}")
    logger.info(f"  Saved metadata to {metadata_file.name}")


def main():
    """Main function to process training PDFs."""

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Ingest PDFs and generate ColPali embeddings')
    parser.add_argument('--limit', type=int, help='Limit number of PDFs to process (for testing)')
    parser.add_argument('--pdfs', type=str, help='Comma-separated list of specific PDFs to process')
    parser.add_argument('--skip-existing', action='store_true', default=True,
                       help='Skip PDFs that have already been processed (default: True)')
    args = parser.parse_args()

    # Setup paths (use Docker paths when running in container)
    if os.path.exists('/app/data'):
        # Running in Docker
        data_dir = Path('/app/data')
        output_dir = Path('/app/embeddings')
    else:
        # Running locally (for development/testing)
        data_dir = Path('../data')
        output_dir = Path('../embeddings')

    pdf_dir = data_dir  # PDFs are directly in data/ directory

    # Create output directory
    output_dir.mkdir(exist_ok=True)

    # Read training data list
    logger.info("Reading training data list...")
    training_files = read_training_data()
    logger.info(f"Found {len(training_files)} training PDFs in TrainingData.md")

    # Filter PDFs based on arguments
    if args.pdfs:
        # Process only specified PDFs
        specified_pdfs = [pdf.strip() for pdf in args.pdfs.split(',')]
        training_files = [f for f in training_files if f in specified_pdfs]
        logger.info(f"Processing only specified PDFs: {training_files}")
    elif args.limit:
        # Limit to first N PDFs
        training_files = training_files[:args.limit]
        logger.info(f"Limiting to first {args.limit} PDFs")

    logger.info(f"Will process {len(training_files)} PDFs")

    # Initialize models
    logger.info("Loading ColPali model...")
    model = ColPaliModel()
    model.load()

    processor = PDFProcessor(dpi=150)

    # Track statistics
    stats = {
        'total_pdfs': len(training_files),
        'processed': 0,
        'failed': 0,
        'total_pages': 0,
        'total_patches': 0,
        'start_time': time.time(),
        'failures': []
    }

    # Process each PDF
    for i, pdf_filename in enumerate(training_files):
        pdf_path = pdf_dir / pdf_filename

        # Check if already processed
        safe_name = pdf_filename.replace('.pdf', '').replace(' ', '_')
        embeddings_file = output_dir / f"{safe_name}_embeddings.pkl"
        metadata_file = output_dir / f"{safe_name}_metadata.json"

        if embeddings_file.exists() and metadata_file.exists():
            logger.info(f"[{i+1}/{len(training_files)}] Skipping {pdf_filename} (already processed)")
            stats['processed'] += 1

            # Load metadata to update stats
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                stats['total_pages'] += metadata['metadata']['page_count']
                for page in metadata['metadata']['pages']:
                    stats['total_patches'] += page['num_patches']
            continue

        if not pdf_path.exists():
            logger.error(f"[{i+1}/{len(training_files)}] PDF not found: {pdf_path}")
            stats['failed'] += 1
            stats['failures'].append(pdf_filename)
            continue

        try:
            logger.info(f"[{i+1}/{len(training_files)}] Processing {pdf_filename}...")
            start_time = time.time()

            # Process PDF
            result = process_pdf(pdf_path, model, processor)

            # Save results
            save_embeddings(pdf_filename, result, output_dir)

            # Update stats
            stats['processed'] += 1
            stats['total_pages'] += result['metadata']['page_count']
            for page in result['metadata']['pages']:
                stats['total_patches'] += page['num_patches']

            elapsed = time.time() - start_time
            logger.info(f"  Completed in {elapsed:.2f} seconds")

        except Exception as e:
            logger.error(f"[{i+1}/{len(training_files)}] Failed to process {pdf_filename}: {e}")
            stats['failed'] += 1
            stats['failures'].append(pdf_filename)

    # Calculate final statistics
    stats['end_time'] = time.time()
    stats['total_time'] = stats['end_time'] - stats['start_time']

    # Save statistics
    stats_file = output_dir / 'ingestion_stats.json'
    with open(stats_file, 'w') as f:
        # Convert times to readable format for JSON
        stats_dict = {
            **stats,
            'total_time_seconds': stats['total_time'],
            'total_time_readable': f"{stats['total_time']/60:.2f} minutes",
            'average_time_per_pdf': f"{stats['total_time']/stats['processed']:.2f} seconds" if stats['processed'] > 0 else "N/A"
        }
        json.dump(stats_dict, f, indent=2)

    # Print summary
    logger.info("\n" + "="*60)
    logger.info("INGESTION COMPLETE")
    logger.info("="*60)
    logger.info(f"Processed: {stats['processed']}/{stats['total_pdfs']} PDFs")
    logger.info(f"Failed: {stats['failed']} PDFs")
    logger.info(f"Total pages: {stats['total_pages']}")
    logger.info(f"Total patches: {stats['total_patches']}")
    logger.info(f"Total time: {stats['total_time']/60:.2f} minutes")

    if stats['processed'] > 0:
        logger.info(f"Average time per PDF: {stats['total_time']/stats['processed']:.2f} seconds")
        logger.info(f"Average patches per page: {stats['total_patches']/stats['total_pages']:.0f}")

    if stats['failures']:
        logger.warning("\nFailed PDFs:")
        for failure in stats['failures']:
            logger.warning(f"  - {failure}")

    logger.info(f"\nResults saved to: {output_dir}")
    logger.info(f"Statistics saved to: {stats_file}")


if __name__ == '__main__':
    main()