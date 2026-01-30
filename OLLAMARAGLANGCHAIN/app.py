import os
import json
import uuid
import datetime
from pathlib import Path

from flask import Flask, request, jsonify, render_template, redirect, url_for, flash

from werkzeug.utils import secure_filename

from langchain_chroma import Chroma
#from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama

# -----------------------------
# Config
# -----------------------------
APP_ROOT = Path(__file__).parent.resolve()
DATA_DIR = APP_ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
CHROMA_DIR = DATA_DIR / "chroma"
INDEX_PATH = DATA_DIR / "docs_index.json"

DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf"}

# Choisis ton modèle Ollama
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.1")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# Chunking
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1200"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Retrieval
TOP_K = int(os.getenv("TOP_K", "6"))

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")


# -----------------------------
# Helpers: index json
# -----------------------------
def load_index():
    if INDEX_PATH.exists():
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    return {"docs": {}}

def save_index(index):
    INDEX_PATH.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def now_iso():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


# -----------------------------
# Vector store (Chroma)
# -----------------------------
def get_embeddings():
    # Ollama doit tourner: `ollama serve`
    return OllamaEmbeddings(model=OLLAMA_EMBED_MODEL)

def get_vectorstore():
    return Chroma(
        collection_name="rag_collection",
        persist_directory=str(CHROMA_DIR),
        embedding_function=get_embeddings(),
    )

def get_llm():
    return Ollama(model=OLLAMA_LLM_MODEL, temperature=0.2)


# -----------------------------
# Ingestion PDF -> Chroma
# -----------------------------
def ingest_pdf(pdf_path: Path, original_filename: str):
    loader = PyPDFLoader(str(pdf_path))
    pages = loader.load()  # liste de Documents, metadata inclut 'page'
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_documents(pages)

    doc_id = str(uuid.uuid4())
    file_stat = pdf_path.stat()

    # enrich metadata
    enriched = []
    for i, d in enumerate(chunks):
        md = dict(d.metadata or {})
        md.update({
            "doc_id": doc_id,
            "chunk_id": i,
            "source_filename": original_filename,
            "source_stored_path": str(pdf_path),
            "mime": "application/pdf",
            "size_bytes": file_stat.st_size,
            "ingested_at": now_iso(),
        })
        d.metadata = md
        enriched.append(d)

    vs = get_vectorstore()
    vs.add_documents(enriched)
    vs.persist()

    # index json (facultatif mais utile)
    index = load_index()
    index["docs"][doc_id] = {
        "doc_id": doc_id,
        "filename": original_filename,
        "stored_path": str(pdf_path),
        "ingested_at": now_iso(),
        "size_bytes": file_stat.st_size,
        "chunks": len(enriched),
        "pages": len(pages),
    }
    save_index(index)

    return {
        "doc_id": doc_id,
        "filename": original_filename,
        "pages": len(pages),
        "chunks": len(enriched),
        "size_bytes": file_stat.st_size,
    }


# -----------------------------
# RAG Chat
# -----------------------------
RAG_SYSTEM = """Tu es un assistant utile.
Tu dois répondre UNIQUEMENT à partir du CONTEXTE fourni.
Si le contexte ne contient pas la réponse, dis clairement que tu ne sais pas à partir des documents.
Toujours citer les sources sous forme: [filename p.X] pour chaque information importante.
Réponds en français.
"""

def build_prompt(question: str, retrieved_docs):
    # On met beaucoup d’infos pour faciliter les citations
    context_parts = []
    for d in retrieved_docs:
        fn = d.metadata.get("source_filename", "unknown.pdf")
        page = d.metadata.get("page", None)
        page_str = f"p.{page + 1}" if isinstance(page, int) else "p.?"
        context_parts.append(f"SOURCE: {fn} {page_str}\n{d.page_content}")

    context = "\n\n---\n\n".join(context_parts)
    return f"""{RAG_SYSTEM}

CONTEXTE:
{context}

QUESTION:
{question}

RÉPONSE (avec citations):"""

def retrieve(question: str):
    vs = get_vectorstore()
    # retourne (Document, score) ; score plus proche de 1 => meilleur (selon la méthode)
    results = vs.similarity_search_with_relevance_scores(question, k=TOP_K)
    docs = [d for (d, s) in results]
    scores = [s for (d, s) in results]
    return results, docs, scores

def chat_rag(question: str):
    results, docs, scores = retrieve(question)
    llm = get_llm()
    prompt = build_prompt(question, docs)
    answer = llm.invoke(prompt)

    # Préparer des "sources" riches pour l’UI
    sources = []
    for (d, s) in results:
        md = d.metadata or {}
        sources.append({
            "score": float(s) if s is not None else None,
            "filename": md.get("source_filename"),
            "doc_id": md.get("doc_id"),
            "page": (md.get("page") + 1) if isinstance(md.get("page"), int) else None,
            "chunk_id": md.get("chunk_id"),
            "preview": d.page_content[:350],
            "metadata": md,  # max info pour debug/inspection
        })

    return answer, sources


# -----------------------------
# Routes
# -----------------------------
@app.get("/")
def home():
    return render_template("index.html")

@app.post("/chat")
def chat():
    data = request.get_json(force=True)
    question = (data.get("message") or "").strip()
    if not question:
        return jsonify({"error": "Message vide"}), 400

    answer, sources = chat_rag(question)
    return jsonify({"answer": answer, "sources": sources})

@app.post("/upload")
def upload():
    if "file" not in request.files:
        flash("Aucun fichier reçu", "error")
        return redirect(url_for("home"))

    f = request.files["file"]
    if f.filename == "":
        flash("Nom de fichier vide", "error")
        return redirect(url_for("home"))

    if not allowed_file(f.filename):
        flash("Extension non supportée (PDF uniquement)", "error")
        return redirect(url_for("home"))

    filename = secure_filename(f.filename)
    # On stocke physiquement le PDF (tu peux choisir de ne pas garder le fichier)
    dest = UPLOAD_DIR / f"{uuid.uuid4()}__{filename}"
    f.save(dest)

    info = ingest_pdf(dest, filename)
    flash(f"PDF ingéré: {info['filename']} ({info['pages']} pages, {info['chunks']} chunks)", "success")
    return redirect(url_for("home"))

@app.get("/docs")
def docs():
    """
    Liste des docs ingérés (index)
    """
    index = load_index()
    docs_list = list(index["docs"].values())
    # Tri par date ingestion desc
    docs_list.sort(key=lambda x: x.get("ingested_at", ""), reverse=True)
    return jsonify({"docs": docs_list})

@app.get("/doc/<doc_id>")
def doc_detail(doc_id):
    """
    Détails maximum depuis Chroma:
    - tous les chunks du doc via where={"doc_id": doc_id}
    - stats pages
    - exemples de chunks
    """
    vs = get_vectorstore()
    # API Chroma sous-jacente
    col = vs._collection

    # Récupère tout (peut être lourd si doc énorme)
    res = col.get(
        where={"doc_id": doc_id},
        include=["metadatas", "documents"]
    )

    metadatas = res.get("metadatas", []) or []
    documents = res.get("documents", []) or []

    # stats
    pages = []
    for md in metadatas:
        p = md.get("page")
        if isinstance(p, int):
            pages.append(p + 1)
    unique_pages = sorted(set(pages))

    # aperçu des premiers chunks
    samples = []
    for i in range(min(12, len(documents))):
        md = metadatas[i] if i < len(metadatas) else {}
        samples.append({
            "chunk_id": md.get("chunk_id"),
            "page": (md.get("page") + 1) if isinstance(md.get("page"), int) else None,
            "filename": md.get("source_filename"),
            "preview": documents[i][:500],
            "metadata": md,
        })

    index = load_index()
    doc_info = index["docs"].get(doc_id)

    return jsonify({
        "doc": doc_info,
        "chroma": {
            "chunks_found": len(documents),
            "unique_pages": unique_pages,
            "samples": samples,
        }
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)

