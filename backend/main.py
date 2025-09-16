from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    return {"filename": file.filename}