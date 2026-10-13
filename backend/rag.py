import os

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Load Groq API Key from .env or environment variable
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set. Please set it in backend/.env or as an environment variable.")
os.environ["GROQ_API_KEY"] = GROQ_API_KEY

VECTOR_DB_DIR = os.path.join(os.path.dirname(__file__), "vector_db")
os.makedirs(VECTOR_DB_DIR, exist_ok=True)

_embeddings = None


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
    return _embeddings


def get_llm():
    global llm
    if llm is None:
        model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        llm = ChatGroq(
            model=model_name,
            temperature=0.3
        )
    return llm


def process_pdf(pdf_path):
    global vector_store

    loader = PyPDFLoader(pdf_path)
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    chunks = splitter.split_documents(documents)
    embeddings = get_embeddings()

    vector_store = FAISS.from_documents(chunks, embeddings)
    vector_store.save_local(VECTOR_DB_DIR)
    print("Vector database saved to:", VECTOR_DB_DIR)


def ask_question(question):
    global vector_store, llm

    if vector_store is None:
        index_file = os.path.join(VECTOR_DB_DIR, "index.faiss")
        if os.path.exists(index_file):
            try:
                print("Loading persisted vector database from disk...")
                vector_store = FAISS.load_local(
                    VECTOR_DB_DIR,
                    get_embeddings(),
                    allow_dangerous_deserialization=True
                )
            except Exception as e:
                print("Error loading persisted FAISS index:", e)

    if vector_store is None:
        return "Please upload a PDF first."

    llm = get_llm()

    docs = vector_store.similarity_search(question, k=3)

    context = "\n\n".join(doc.page_content for doc in docs)

    prompt = f"""
You are a helpful AI assistant.

Answer ONLY from the context below.

If the answer is not found in the context, reply:
'I couldn't find the answer in the uploaded PDF.'

Context:
{context}

Question:
{question}
"""

    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        # Automatic fallback to alternative available Groq models
        for fallback_model in ["openai/gpt-oss-20b", "qwen/qwen3.8-27b"]:
            try:
                fallback_llm = ChatGroq(model=fallback_model, temperature=0.3)
                response = fallback_llm.invoke(prompt)
                llm = fallback_llm
                return response.content
            except Exception:
                continue
        raise e