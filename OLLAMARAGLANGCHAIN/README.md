# Flask RAG Chatbot with Ollama, LangChain & Chroma

![Ollamaragchroma](https://github.com/zebulon75018/LLMStuff/blob/main/img/ollamaragchroma.png?raw=true)



A web-based Retrieval-Augmented Generation (RAG) chatbot built with Flask, LangChain, Ollama, and ChromaDB.

This application allows users to:

- Chat with a local LLM via Ollama
- Upload multiple PDF files via a web interface
- Automatically index PDFs into a persistent Chroma vector database
- Ask questions answered only from the uploaded documents
- View detailed metadata, chunks, pages, and similarity scores for each document

The project is designed to run locally on Linux, fully offline (except for model downloads).

## Features

- 🧠 **Local LLM via Ollama**
- 📚 **Multi-document RAG** (all uploaded PDFs are used, not just the first one)
- 📄 **PDF ingestion** with metadata enrichment
- 🔍 **Semantic search** using ChromaDB
- 🧩 **Chunk-level traceability** (page number, chunk ID, similarity score)
- 🖥️ **Simple web UI** (chat, upload, document browser)
- 💾 **Persistent vector database** on disk
- 🇫🇷 **French answers** (configurable)

## Tech Stack

- **Backend:** Flask (Python)
- **LLM orchestration:** LangChain
- **LLM runtime:** Ollama
- **Vector database:** ChromaDB
- **Embeddings:** Ollama embeddings (nomic-embed-text)
- **PDF parsing:** PyPDF
- **Frontend:** HTML + vanilla JavaScript

## Architecture Overview

```
User (Browser)
   |
   |  Upload PDF / Ask Question
   v
Flask Web App
   |
   |-- PDF Loader (PyPDF)
   |-- Text Splitter (LangChain)
   |-- Embeddings (Ollama)
   |-- Vector Store (ChromaDB, persistent)
   |
   |-- Retrieval (Similarity Search)
   |-- Prompt Construction
   v
Ollama LLM
   |
   v
Answer + Sources (pages, chunks, scores)
```

## Requirements

- Linux (tested on Ubuntu)
- Python 3.10+
- Ollama installed and running

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/flask-rag-ollama.git
   cd flask-rag-ollama
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Ollama Setup

1. **Install Ollama**
   👉 [https://ollama.com](https://ollama.com)

2. **Start Ollama**
   ```bash
   ollama serve
   ```

3. **Pull required models**
   ```bash
   ollama pull llama3.1
   ollama pull nomic-embed-text
   ```

You can change models using environment variables (see below).

## Running the Application

```bash
python app.py
```

Then open your browser at:
[http://localhost:5000](http://localhost:5000)

## Usage

### Upload PDFs
Use the **Upload PDF** section in the UI. Each uploaded PDF is:
- Parsed page by page
- Split into chunks
- Embedded and stored in ChromaDB
- Enriched with metadata (filename, page, chunk ID, size, ingestion time)

### Chat with the Documents
Ask questions in the chat box. The assistant:
- Retrieves relevant chunks from all uploaded PDFs
- Answers only from document content
- Cites sources with filename and page number

### Explore the Knowledge Base
View the list of ingested documents. Inspect:
- Number of pages and chunks
- Stored metadata
- Example chunks
- Pages present in the vector database

## API Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | GET | Web interface |
| `/upload` | POST | Upload and ingest a PDF |
| `/chat` | POST | Ask a RAG question |
| `/docs` | GET | List ingested documents |
| `/doc/<doc_id>` | GET | Detailed document info from Chroma |
| `/stats` | GET | Vector database statistics |

## Environment Variables

Optional configuration:

```bash
export OLLAMA_LLM_MODEL=llama3.1
export OLLAMA_EMBED_MODEL=nomic-embed-text
export CHUNK_SIZE=1200
export CHUNK_OVERLAP=200
export TOP_K=6
export FLASK_SECRET_KEY=your-secret-key
```

## Data Storage

```
data/
├── uploads/        # Uploaded PDF files
├── chroma/         # Persistent Chroma vector database
└── docs_index.json # Document metadata index
```

## Troubleshooting

### Only one PDF is used in RAG
✅ **Fixed by:**
- Using a single persistent Chroma collection
- Absolute `persist_directory`
- Singleton vector store instance
- Explicit chunk IDs

Check `/stats` to verify total chunk count.

## Roadmap / Possible Improvements

- Streaming responses (token-by-token)
- Filter chat by selected document(s)
- Search inside a single PDF
- Duplicate PDF detection (SHA256 hash)
- Authentication / multi-user support
- Docker (Flask + Ollama)
- Better UI (React / Vue)

## License

MIT License
