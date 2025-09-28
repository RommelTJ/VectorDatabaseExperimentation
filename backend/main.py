from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import logging
from PIL import Image
from adapters import get_database_adapter
from colpali_model import colpali_model
from pdf_processor import pdf_processor

app = FastAPI()

VECTOR_DB_TYPE = os.environ.get("VECTOR_DB_TYPE", "postgres")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Preload the ColPali model at startup to avoid memory issues during requests"""
    print("Starting up... preloading ColPali model")
    try:
        colpali_model.load()
        print("ColPali model preloaded successfully")
    except Exception as e:
        print(f"Failed to preload ColPali model: {e}")
        # Don't fail startup, but log the issue
        pass

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "backend"}

@app.get("/api/config")
async def get_config():
    return {
        "vector_db_type": VECTOR_DB_TYPE,
        "supported_databases": [
            "postgres",
            "qdrant",
            "redis",
            "elasticsearch",
            "milvus",
            "weaviate",
            "mongodb"
        ]
    }

@app.get("/api/db/test-connection")
async def test_db_connection():
    """Test database connection"""
    try:
        db_adapter = get_database_adapter(VECTOR_DB_TYPE)
        await db_adapter.connect()
        await db_adapter.disconnect()
        return {
            "status": "success",
            "database": VECTOR_DB_TYPE,
            "message": f"Successfully connected to {VECTOR_DB_TYPE}"
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/db/create-collection")
async def create_collection(collection_name: str = "patterns"):
    """Create a collection/table for storing vectors"""
    try:
        db_adapter = get_database_adapter(VECTOR_DB_TYPE)
        await db_adapter.connect()
        await db_adapter.create_collection(collection_name, dimension=128)  # ColPali uses 128 dimensions
        await db_adapter.disconnect()
        return {
            "status": "success",
            "database": VECTOR_DB_TYPE,
            "collection": collection_name,
            "message": f"Successfully created collection '{collection_name}' in {VECTOR_DB_TYPE}"
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/db/delete-pdf/{pdf_id}")
async def delete_pdf(pdf_id: str):
    """Delete a PDF and all its embeddings from the database"""
    try:
        db_adapter = get_database_adapter(VECTOR_DB_TYPE)
        await db_adapter.connect()
        await db_adapter.delete("patterns", [pdf_id])
        await db_adapter.disconnect()

        return {
            "status": "success",
            "database": VECTOR_DB_TYPE,
            "deleted_pdf": pdf_id,
            "message": f"Successfully deleted PDF '{pdf_id}' from {VECTOR_DB_TYPE}"
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/db/test-insert")
async def test_insert_embeddings(num_pdfs: int = 2):
    """Test inserting embeddings from cache"""
    import json
    import pickle
    from pathlib import Path

    try:
        db_adapter = get_database_adapter(VECTOR_DB_TYPE)
        await db_adapter.connect()

        # Get list of embedding files (pkl files)
        embeddings_dir = Path("/app/data/embeddings")
        embedding_files = sorted(list(embeddings_dir.glob("*_embeddings.pkl")))[:num_pdfs]

        if not embedding_files:
            raise HTTPException(status_code=404, detail="No embedding files found in cache")

        total_inserted = 0
        for emb_file in embedding_files:
            # Load embeddings from pickle file
            with open(emb_file, 'rb') as f:
                embeddings_data = pickle.load(f)

            # Load metadata from corresponding JSON file
            metadata_file = emb_file.parent / emb_file.name.replace('_embeddings.pkl', '_metadata.json')
            with open(metadata_file, 'r') as f:
                metadata_info = json.load(f)

            pdf_name = metadata_info['metadata']['pdf_name']
            pdf_id = pdf_name.replace('.pdf', '')

            # Process each page
            for page_idx, page_info in enumerate(metadata_info['metadata']['pages']):
                page_embeddings = embeddings_data[page_idx]  # Shape: (num_patches, 128)

                # Create metadata for each patch
                metadata_list = []
                for patch_idx in range(page_info['num_patches']):
                    metadata_list.append({
                        'pdf_id': pdf_id,
                        'page_num': page_idx,
                        'patch_index': patch_idx,
                        'title': pdf_name
                    })

                # Convert embeddings to list format
                embeddings_list = page_embeddings.tolist()

                # Insert this page's embeddings
                await db_adapter.insert("patterns", embeddings_list, metadata_list)
                total_inserted += len(metadata_list)
                print(f"Inserted {len(metadata_list)} embeddings for {pdf_name} page {page_idx}")

        await db_adapter.disconnect()

        return {
            "status": "success",
            "database": VECTOR_DB_TYPE,
            "files_processed": len(embedding_files),
            "total_embeddings": total_inserted,
            "message": f"Successfully inserted {total_inserted} embeddings from {len(embedding_files)} PDFs"
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class TextSearchRequest(BaseModel):
    query: str
    limit: int = 10

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload PDF and store embeddings in vector database"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        # Read PDF and generate embeddings
        pdf_bytes = await file.read()
        images = pdf_processor.pdf_to_images(pdf_bytes)
        embeddings = colpali_model.embed_images(images)

        # Prepare data for insertion
        pdf_id = file.filename.replace('.pdf', '')

        # Save cover page as thumbnail
        import os
        from pathlib import Path
        thumbnail_dir = Path("/app/data/thumbnails")
        thumbnail_dir.mkdir(parents=True, exist_ok=True)

        cover_thumbnail = images[0]  # First page (cover)
        thumbnail_path = thumbnail_dir / f"{pdf_id}.jpg"

        # Resize to smaller thumbnail (max width 300px, maintain aspect ratio)
        max_width = 300
        aspect_ratio = cover_thumbnail.height / cover_thumbnail.width
        new_width = min(cover_thumbnail.width, max_width)
        new_height = int(new_width * aspect_ratio)

        resized_thumbnail = cover_thumbnail.resize((new_width, new_height), Image.Resampling.LANCZOS)
        resized_thumbnail.save(thumbnail_path, "JPEG", quality=85, optimize=True)

        all_vectors = []
        all_metadata = []

        # Process embeddings for each page
        for page_idx in range(len(images)):
            page_embeddings = embeddings[page_idx]  # Shape: (num_patches, 128)

            for patch_idx in range(len(page_embeddings)):
                all_vectors.append(page_embeddings[patch_idx].cpu().numpy().tolist())
                all_metadata.append({
                    'pdf_id': pdf_id,
                    'page_num': page_idx,
                    'patch_index': patch_idx,
                    'title': file.filename
                })

        # Insert into database
        db_adapter = get_database_adapter(VECTOR_DB_TYPE)
        await db_adapter.connect()
        await db_adapter.insert("patterns", all_vectors, all_metadata)
        await db_adapter.disconnect()

        return {
            "filename": file.filename,
            "pages": len(images),
            "embeddings_stored": len(all_vectors),
            "status": "success"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/api/search/text")
async def search_text(request: TextSearchRequest):
    """Search patterns using text query"""
    try:
        # Generate embedding for query
        query_embeddings = colpali_model.embed_queries([request.query])

        # ColPali returns shape (1, num_patches, 128) for queries
        # We need to flatten to get all patch embeddings and average them
        query_tensor = query_embeddings[0]  # Remove batch dimension

        # Average across all patches to get a single 128-dim vector
        import torch
        query_vector = torch.mean(query_tensor, dim=0).cpu().numpy().tolist()

        # Search in database
        db_adapter = get_database_adapter(VECTOR_DB_TYPE)
        await db_adapter.connect()
        results = await db_adapter.search(
            collection_name="patterns",
            query_vector=query_vector,
            top_k=request.limit
        )
        await db_adapter.disconnect()

        return {
            "query": request.query,
            "results": results,
            "count": len(results)
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search/image")
async def search_image(file: UploadFile = File(...)):
    """Search patterns using an image"""
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    try:
        # Read image and generate embedding
        from PIL import Image
        import io

        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Generate embedding for image using ColPali
        embeddings = colpali_model.embed_images([image])

        # Average all patch embeddings to get a single vector
        import torch
        query_tensor = embeddings[0]  # Shape: (num_patches, 128)
        query_vector = torch.mean(query_tensor, dim=0).cpu().numpy().tolist()

        # Search in database
        db_adapter = get_database_adapter(VECTOR_DB_TYPE)
        await db_adapter.connect()
        results = await db_adapter.search(
            collection_name="patterns",
            query_vector=query_vector,
            top_k=10
        )
        await db_adapter.disconnect()

        return {
            "results": results,
            "count": len(results)
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process/pdf")
async def process_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        pdf_bytes = await file.read()
        pdf_info = pdf_processor.get_pdf_info(pdf_bytes)
        pdf_info["filename"] = file.filename
        pdf_info["size_bytes"] = len(pdf_bytes)
        return pdf_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/api/embeddings/generate")
async def generate_embeddings(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        pdf_bytes = await file.read()
        images = pdf_processor.pdf_to_images(pdf_bytes)

        embeddings = colpali_model.embed_images(images)

        return {
            "filename": file.filename,
            "page_count": len(images),
            "embeddings_shape": list(embeddings.shape),
            "embeddings_dtype": str(embeddings.dtype),
            "device": str(embeddings.device)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating embeddings: {str(e)}")

@app.post("/api/embeddings/query")
async def embed_query(request: TextSearchRequest):
    try:
        embeddings = colpali_model.embed_queries([request.query])

        return {
            "query": request.query,
            "embeddings_shape": list(embeddings.shape),
            "embeddings_dtype": str(embeddings.dtype),
            "device": str(embeddings.device)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error embedding query: {str(e)}")
