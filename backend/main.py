from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import logging
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

class TextSearchRequest(BaseModel):
    query: str
    limit: int = 10

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    return {"filename": file.filename}

@app.post("/api/search/text")
async def search_text(request: TextSearchRequest):
    try:
        db_adapter = get_database_adapter(VECTOR_DB_TYPE)
        results = await db_adapter.search(
            collection_name="patterns",
            query_vector=[0.0] * 128,
            top_k=request.limit
        )
        return {"results": results}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search/image")
async def search_image(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    try:
        db_adapter = get_database_adapter(VECTOR_DB_TYPE)
        results = await db_adapter.search(
            collection_name="patterns",
            query_vector=[0.0] * 128,
            top_k=10
        )
        return {"results": results}
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