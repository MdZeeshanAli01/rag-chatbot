from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
import os
import shutil
import asyncio

from rag import process_pdf, ask_question

app = FastAPI(title="RAG Chatbot API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


# AWS S3 Integration
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


def upload_to_s3(file_path: str, file_name: str):
    """Uploads document to Amazon S3 bucket if configured"""
    if not S3_BUCKET_NAME:
        return None
    try:
        import boto3
        s3_client = boto3.client("s3", region_name=AWS_REGION)
        s3_key = f"documents/{file_name}"
        s3_client.upload_file(file_path, S3_BUCKET_NAME, s3_key)
        print(f"Successfully synced {file_name} to Amazon S3: s3://{S3_BUCKET_NAME}/{s3_key}")
        return s3_key
    except Exception as e:
        print(f"Warning: S3 sync skipped or failed ({str(e)}). File saved locally on EBS.")
        return None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "message": "RAG Chatbot Backend is Running",
        "s3_bucket": S3_BUCKET_NAME or "Not configured"
    }


@app.get("/s3-files")
def list_s3_files():
    """Lists files currently in the Amazon S3 bucket"""
    if not S3_BUCKET_NAME:
        return {"configured": False, "message": "S3_BUCKET_NAME not set in environment."}
    try:
        import boto3
        s3_client = boto3.client("s3", region_name=AWS_REGION)
        resp = s3_client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix="documents/")
        files = []
        for obj in resp.get("Contents", []):
            files.append({
                "key": obj["Key"],
                "size_kb": round(obj["Size"] / 1024, 2),
                "last_modified": str(obj["LastModified"])
            })
        return {
            "configured": True,
            "bucket": S3_BUCKET_NAME,
            "count": len(files),
            "files": files
        }
    except Exception as e:
        return {"configured": True, "error": str(e)}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)

        # 1. Save uploaded PDF to local EBS storage
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        print("PDF Saved to EBS:", file_path)

        # 2. Sync to Amazon S3 (Object Storage) if configured
        s3_key = await asyncio.to_thread(upload_to_s3, file_path, file.filename)

        # 3. Process PDF into FAISS vector database
        await asyncio.to_thread(process_pdf, file_path)

        print("PDF Processed Successfully!")

        response_msg = "PDF uploaded and processed successfully."
        if s3_key:
            response_msg += f" (Synced to Amazon S3 bucket: {S3_BUCKET_NAME})"

        return {
            "message": response_msg,
            "s3_synced": bool(s3_key),
            "s3_bucket": S3_BUCKET_NAME
        }

    except Exception as e:
        print("UPLOAD ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ask")
async def ask(query: str):
    try:
        answer = await asyncio.to_thread(ask_question, query)
        return {
            "question": query,
            "answer": answer
        }

    except Exception as e:
        print("ASK ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Serve Frontend files directly from FastAPI if available
if os.path.exists(FRONTEND_DIR):
    @app.get("/")
    def serve_frontend_index():
        index_file = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "RAG Chatbot Backend is Running"}

    app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")
else:
    @app.get("/")
    def home():
        return {"message": "RAG Chatbot Backend is Running"}