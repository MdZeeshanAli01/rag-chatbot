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

vector_store = None
llm = None


def process_pdf(pdf_path):
    global vector_store, llm

    loader = PyPDFLoader(pdf_path)
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    chunks = splitter.split_documents(documents)

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vector_store = FAISS.from_documents(chunks, embeddings)

    # Use currently supported production model on Groq
    model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    llm = ChatGroq(
        model=model_name,
        temperature=0.3
    )


def ask_question(question):
    global vector_store, llm

    if vector_store is None:
        return "Please upload a PDF first."

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