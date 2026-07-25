"""
ingest.py
Reads the Constitution PDF using PyMuPDF, strips footnote noise, builds:
- A FAISS semantic index (for general/conceptual questions)
- A direct article-number lookup table (for "what does Article X say")
- A full-page text index (so we can pull complete page context, avoiding
  lost information at chunk boundaries)
"""

import re
import json
import fitz  # PyMuPDF
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

PDF_PATH = "data/constitution.pdf"
INDEX_PATH = "vectorstore/faiss_index"
ARTICLE_INDEX_PATH = "vectorstore/article_index.json"
PAGE_INDEX_PATH = "vectorstore/page_index.json"

FOOTNOTE_LINE = re.compile(
    r'^\s*\d{1,2}\s*(Subs\.|Ins\.|Added|Omitted|Repealed|New\b|Entries|Proviso|Explanation)',
    re.IGNORECASE,
)
SEPARATOR_LINE = re.compile(r'^[\s\-–_]{5,}$')

ARTICLE_HEADING = re.compile(r'(?:^|\n)\s*(?:\d{1,3}\[)?(\d{1,3}[A-Z]{0,2})\.\s+')

FRONT_MATTER_FOOTER = re.compile(
    r'CONSTITUTION OF PAKISTAN\s*\(([ivxlcdm]+)\)', re.IGNORECASE
)


def is_front_matter(text: str) -> bool:
    return bool(FRONT_MATTER_FOOTER.search(text))


def clean_page_text(text: str) -> str:
    cleaned_lines = []
    for line in text.split("\n"):
        if FOOTNOTE_LINE.match(line):
            continue
        if SEPARATOR_LINE.match(line):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def load_pdf_documents(path: str):
    documents = []
    pdf = fitz.open(path)
    for i, page in enumerate(pdf):
        text = page.get_text("text")
        documents.append(Document(page_content=text, metadata={"page": i}))
    pdf.close()
    return documents


def build_article_index(documents):
    index = {}
    for doc in documents:
        text = doc.page_content
        page = doc.metadata.get("page")

        if is_front_matter(text):
            continue

        matches = list(ARTICLE_HEADING.finditer(text))
        for i, m in enumerate(matches):
            num = m.group(1)
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            article_text = text[start:end].strip()
            if len(article_text) < 20:
                continue
            if num not in index:
                index[num] = {"text": article_text, "page": page}
    return index


def main():
    print("Loading PDF with PyMuPDF...")
    documents = load_pdf_documents(PDF_PATH)
    print(f"Loaded {len(documents)} pages.")

    print("Cleaning footnote noise from each page...")
    for doc in documents:
        doc.page_content = clean_page_text(doc.page_content)

    print("Saving full-page text index...")
    page_index = {str(doc.metadata["page"]): doc.page_content for doc in documents}
    with open(PAGE_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(page_index, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(page_index)} pages to {PAGE_INDEX_PATH}")

    print("Building article-number lookup index...")
    article_index = build_article_index(documents)
    with open(ARTICLE_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(article_index, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(article_index)} articles to {ARTICLE_INDEX_PATH}")

    print("Splitting into chunks for semantic search...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\nArticle", "\n\n", "\n", ". ", " "],
    )

    chunks = []
    for doc in documents:
        text = doc.page_content
        page = doc.metadata.get("page")
        headings = [(m.start(), m.group(1)) for m in ARTICLE_HEADING.finditer(text)]
        pieces = splitter.split_text(text)
        search_from = 0
        for piece in pieces:
            idx = text.find(piece, search_from)
            if idx == -1:
                idx = text.find(piece)
            article_num = None
            for h_pos, h_num in headings:
                if h_pos <= idx:
                    article_num = h_num
                else:
                    break
            chunks.append(Document(
                page_content=piece,
                metadata={"page": page, "article": article_num},
            ))
            search_from = max(idx + 1, search_from)

    junk_words = ["Amdt.", "ibid", "Subs.", "P.O. No.", "w.e.f"]
    filtered_chunks = []
    for c in chunks:
        text = c.page_content.strip()
        if len(text) < 40:
            continue
        junk_hits = sum(text.count(w) for w in junk_words)
        if junk_hits >= 3:
            continue
        filtered_chunks.append(c)

    print(f"Created {len(chunks)} chunks, kept {len(filtered_chunks)} after junk filtering.")

    print("Loading local embedding model...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    print("Building FAISS index...")
    vectorstore = FAISS.from_documents(filtered_chunks, embeddings)
    vectorstore.save_local(INDEX_PATH)
    print(f"Done. FAISS index saved to {INDEX_PATH}")


if __name__ == "__main__":
    main()