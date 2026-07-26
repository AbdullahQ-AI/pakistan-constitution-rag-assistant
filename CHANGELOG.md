# Changelog

Development history and key engineering decisions for the Pakistan Constitution Q&A Assistant.

## v1.3 — Evaluation & Documentation
- Added automated evaluation script (`src/evaluate.py`) — 19/19 (100%) pass rate across citation accuracy and off-topic refusal tests
- Documented all major debugging challenges in the README
- Added architecture diagram and polished UI (light theme, sidebar examples)

## v1.2 — Retrieval Quality Fixes
- **Problem:** Conceptual questions like "Who can become Prime Minister?" returned false negatives, even though the answer existed in the document (Articles 90–91), because it was split across a chunk boundary.
- **Fix:** Switched from chunk-level to page-level retrieval (with neighboring-page expansion), so relevant context is no longer lost at arbitrary chunk cutoffs.
- Added a keyword-search fallback alongside semantic search to catch exact-phrase matches embeddings sometimes miss.
- Added an off-topic detection rule so the system declines unrelated questions instead of guessing.

## v1.1 — Article Lookup Accuracy Fixes
- **Problem:** Direct lookups for specific articles (e.g. "What is Article 9A about?") sometimes returned Table-of-Contents entries or unrelated Schedule clauses instead of the real article text.
- **Fix:** Added detection and exclusion of front-matter/Contents pages (by their distinctive footer format), and fixed the article-heading regex to tolerate amendment-history bracket prefixes (e.g. `3[9A. ...]`).
- Fixed a bug where duplicate article numbers (real article vs. an unrelated Schedule reference) picked the wrong match — now takes the first (correct) occurrence instead of the longest.

## v1.0 — Initial RAG Pipeline
- Built ingestion pipeline: PDF → PyMuPDF text extraction → footnote-noise removal → chunking → local embeddings (sentence-transformers) → FAISS index
- **Problem:** Default `pypdf` extraction corrupted word spacing (e.g. "Article" became "A rticle"). Switched to PyMuPDF for accurate extraction.
- **Problem:** Legal footnotes ("Subs. by the Constitution (Eighteenth Amdt.)...") were polluting semantic search results, since they mention "Article" more often than the real article text. Added regex-based footnote filtering during ingestion.
- Connected Gemini (free tier) via LangChain for answer generation, with a citation-enforcing system prompt
- Built a Streamlit chat UI and deployed to Streamlit Community Cloud
- **Problem:** Free-tier Gemini model names (`gemini-1.5-flash`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`) were deprecated for new users in rapid succession during development. Switched to Google's `-latest` model aliases, which stay pointed at a currently-available model.