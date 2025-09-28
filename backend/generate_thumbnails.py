#!/usr/bin/env python3
"""
Script to generate thumbnails for existing PDFs in the data directory.
Run this locally (not in Docker) to create thumbnails for PDFs that were loaded before thumbnails were implemented.
"""

from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image
import sys

def generate_thumbnail(pdf_path, output_dir, max_width=300):
    """Generate a thumbnail for the cover page of a PDF."""
    try:
        # Get PDF filename without extension for thumbnail name
        pdf_id = pdf_path.stem

        # Convert first page to image
        images = convert_from_path(pdf_path, dpi=150, first_page=1, last_page=1)

        if not images:
            print(f"  ❌ No pages found in {pdf_path.name}")
            return False

        cover_image = images[0]

        # Calculate new dimensions maintaining aspect ratio
        aspect_ratio = cover_image.height / cover_image.width
        new_width = min(cover_image.width, max_width)
        new_height = int(new_width * aspect_ratio)

        # Resize image
        thumbnail = cover_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Save thumbnail
        thumbnail_path = output_dir / f"{pdf_id}.jpg"
        thumbnail.save(thumbnail_path, "JPEG", quality=85, optimize=True)

        print(f"  ✓ Generated thumbnail for {pdf_path.name} ({new_width}x{new_height})")
        return True

    except Exception as e:
        print(f"  ❌ Error processing {pdf_path.name}: {e}")
        return False

def main():
    # Set up paths - in Docker, data is at /app/data
    import os
    if os.path.exists("/app/data"):
        # Running in Docker
        data_dir = Path("/app/data")
    else:
        # Running locally
        backend_dir = Path(__file__).parent
        project_root = backend_dir.parent
        data_dir = project_root / "data"

    thumbnail_dir = data_dir / "thumbnails"

    # Create thumbnail directory if it doesn't exist
    thumbnail_dir.mkdir(parents=True, exist_ok=True)

    # Get all PDF files
    pdf_files = list(data_dir.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found in data directory")
        sys.exit(0)

    print(f"Found {len(pdf_files)} PDF files")
    print(f"Generating thumbnails in {thumbnail_dir}...")
    print()

    success_count = 0
    skip_count = 0

    for pdf_path in pdf_files:
        pdf_id = pdf_path.stem
        thumbnail_path = thumbnail_dir / f"{pdf_id}.jpg"

        # Skip if thumbnail already exists
        if thumbnail_path.exists():
            print(f"  → Skipping {pdf_path.name} (thumbnail exists)")
            skip_count += 1
            continue

        if generate_thumbnail(pdf_path, thumbnail_dir):
            success_count += 1

    print()
    print(f"Summary:")
    print(f"  - Generated: {success_count} thumbnails")
    print(f"  - Skipped: {skip_count} (already exist)")
    print(f"  - Failed: {len(pdf_files) - success_count - skip_count}")

if __name__ == "__main__":
    main()