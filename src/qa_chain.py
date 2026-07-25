"""
qa_chain.py
Hybrid retrieval:
- Specific Article number -> direct lookup (article_index.json)
- Otherwise -> semantic + keyword search finds relevant PAGES, then we
  pull the FULL page text (plus neighboring pages) so context isn't
  lost at chunk boundaries.
"""

import os
import re
import json
from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

INDEX_PATH = "vectorstore/faiss_index"
ARTICLE_INDEX_PATH = "vectorstore/article_index.json"
PAGE_INDEX_PATH = "vectorstore/page_index.json"

ARTICLE_NUMBER_IN_QUESTION = re.compile(r'article\s+(\d{1,3}[A-Z]{0,2})', re.IGNORECASE)

SYSTEM_PROMPT = """You are a knowledgeable, friendly assistant that explains the \
Constitution of Pakistan in plain language, using ONLY the provided context excerpts.

Format every answer like this:
1. Start with a short 1-2 sentence direct answer to the question.
2. Then give supporting detail as a bulleted list if there are multiple points, \
using **bold** for key terms (e.g. **Article 25**, **equality before law**).
3. Keep language simple and conversational — explain legal terms in everyday words.
4. Always cite the specific Article number(s) inline, e.g. "According to **Article 25**...".

Rules:
- Answer ONLY using the information in the context below. Do not use outside knowledge.
- If the question IS about the Constitution, law, government, or rights in Pakistan, \
but the provided context does not contain the answer, say clearly: \
"I couldn't find this in the sections of the Constitution I have access to."
- If the question is COMPLETELY UNRELATED to the Constitution of Pakistan (e.g. general \
knowledge, current events, other countries, technology, entertainment, personal advice), \
do NOT search the context for an answer. Instead respond ONLY with: \
"I'm designed specifically to answer questions about the Constitution of Pakistan, so I'm \
not able to help with that here. Feel free to ask me anything about the Constitution instead!"
- Never guess or make anything up.
- Do not repeat the disclaimer or context labels like "[Page X]" in your answer text.
- End every answer with this exact line on its own (skip this line ONLY for the \
off-topic response above): \
"⚠️ *This is informational only and not legal advice.*"
"""


def load_vectorstore():
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return FAISS.load_local(INDEX_PATH, embeddings, allow_dangerous_deserialization=True)


def load_article_index():
    with open(ARTICLE_INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_page_index():
    with open(PAGE_INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_llm():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found. Check your .env file.")
    return ChatGoogleGenerativeAI(model="gemini-flash-latest", google_api_key=api_key, temperature=0)


def keyword_boost_search(question, vectorstore, k=5):
    stopwords = {"the", "is", "are", "a", "an", "of", "to", "in", "what", "who",
                 "how", "can", "does", "do", "for", "on", "and", "or", "be"}
    words = [w.strip("?.,").lower() for w in question.split()]
    keywords = [w for w in words if w not in stopwords and len(w) > 2]

    all_docs = list(vectorstore.docstore._dict.values())
    scored = []
    for doc in all_docs:
        text_lower = doc.page_content.lower()
        score = sum(text_lower.count(kw) for kw in keywords)
        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored[:k]]


def answer_question(question, vectorstore, llm, article_index=None, page_index=None, k=10):
    used_pages = []

    direct_hit = None
    match = ARTICLE_NUMBER_IN_QUESTION.search(question)
    if match and article_index:
        number = match.group(1)
        direct_hit = article_index.get(number)

    if direct_hit:
        context = f"[Page {direct_hit['page']}]\n{direct_hit['text']}"
        used_pages = [direct_hit['page']]
    else:
        semantic_docs = vectorstore.similarity_search(question, k=k)
        keyword_docs = keyword_boost_search(question, vectorstore, k=5)

        pages_found = set()
        for doc in semantic_docs + keyword_docs:
            p = doc.metadata.get("page")
            if p is not None:
                pages_found.add(p)

        expanded_pages = set()
        for p in pages_found:
            expanded_pages.add(p)
            expanded_pages.add(p + 1)
            expanded_pages.add(p - 1)

        context_parts = []
        if page_index:
            for p in sorted(pg for pg in expanded_pages if pg >= 0):
                text = page_index.get(str(p))
                if text:
                    context_parts.append(f"[Page {p}]\n{text}")
                    used_pages.append(p)

        context = "\n\n---\n\n".join(context_parts)

    full_prompt = f"{SYSTEM_PROMPT}\n\nContext:\n{context}\n\nQuestion: {question}\n\nAnswer:"
    response = llm.invoke(full_prompt)

    return response.content, used_pages


if __name__ == "__main__":
    vectorstore = load_vectorstore()
    article_index = load_article_index()
    page_index = load_page_index()
    llm = build_llm()

    question = "Who can become Prime Minister of Pakistan?"
    answer, pages = answer_question(question, vectorstore, llm, article_index, page_index)

    print("QUESTION:", question)
    print("\nANSWER:\n", answer)
    print("\nSOURCE PAGES USED:", pages)