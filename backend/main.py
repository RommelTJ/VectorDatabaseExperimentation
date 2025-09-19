from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

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
    raise HTTPException(
        status_code=501,
        detail=f"Text search not implemented for {VECTOR_DB_TYPE} database"
    )

@app.post("/api/search/image")
async def search_image(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    raise HTTPException(
        status_code=501,
        detail=f"Image search not implemented for {VECTOR_DB_TYPE} database"
    )