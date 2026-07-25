# 📜 Pakistan Constitution Q&A Assistant

A Retrieval-Augmented Generation (RAG) chatbot that answers questions about the Constitution of Pakistan in plain language, with accurate article-level citations — built entirely with free, open-source tools.

🔗 **Live demo:** https://pak-constitution-bot.streamlit.app/

## Features

- Answers questions about the Constitution using **only** the official text — no hallucinated legal claims
- Every answer cites the specific **Article number(s)** it's based on
- Hybrid retrieval: direct lookup for specific articles (e.g. "What is Article 25 about?") + semantic + keyword search for conceptual questions (e.g. "How can the Constitution be amended?")
- Gracefully declines to answer questions unrelated to the Constitution
- Clean, minimal chat interface built with Streamlit

## Tech Stack

| Component | Tool |
|---|---|
| PDF parsing | PyMuPDF |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) — runs locally, no API cost |
| Vector store | FAISS (local) |
| LLM | Google Gemini (free tier) via LangChain |
| UI | Streamlit |

## How it works

1. **Ingestion** (`src/ingest.py`): Parses the official Constitution PDF, cleans footnote/amendment-history noise, and builds three indexes:
   - A FAISS vector index for semantic search over the full text
   - A direct article-number lookup table for precise citations
   - A full-page text index (used to avoid losing context at chunk boundaries)
2. **Retrieval** (`src/qa_chain.py`): For a given question, either does a direct article lookup (if a specific Article number is mentioned) or combines semantic + keyword search to find relevant pages.
3. **Generation**: The retrieved context is passed to Gemini with a system prompt that enforces citation and prevents hallucination.
4. **UI** (`src/app.py`): A Streamlit chat interface presents the pipeline.

## Running locally

```bash
git clone https://github.com/AbdullahQ-AI/pakistan-constitution-rag-assistant.git
cd pakistan-constitution-rag-assistant
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

Create a `.env` file with your free [Google AI Studio](https://aistudio.google.com/app/apikey) API key: