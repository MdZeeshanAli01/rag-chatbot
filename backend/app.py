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


@app.get("/health")
def health():
    return {"status": "ok", "message": "RAG Chatbot Backend is Running"}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)

        # Save uploaded PDF
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        print("PDF Saved:", file_path)

        # Process PDF in threadpool to prevent blocking the asyncio event loop
        await asyncio.to_thread(process_pdf, file_path)

        print("PDF Processed Successfully!")

        return {
            "message": "PDF uploaded and processed successfully."
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