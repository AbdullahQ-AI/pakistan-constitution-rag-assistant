"""
app.py
Streamlit chat interface for the Pakistan Constitution Q&A Assistant.
"""

import streamlit as st
from qa_chain import load_vectorstore, load_article_index, load_page_index, build_llm, answer_question

st.set_page_config(page_title="Pakistan Constitution Q&A", page_icon="📜", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; }
.stApp { background-color: #ffffff; }
[data-testid="stSidebar"] { background-color: #fafafa; border-right: 1px solid #e5e5e5; }
[data-testid="stSidebar"] h3 { font-size: 0.95rem; font-weight: 600; color: #333; }
[data-testid="stSidebar"] p { color: #555; font-size: 0.88rem; line-height: 1.5; }
[data-testid="stSidebar"] button {
    background-color: #ffffff !important; color: #333 !important;
    border: 1px solid #e0e0e0 !important; border-radius: 8px !important;
    text-align: left !important; font-size: 0.85rem !important; padding: 10px 12px !important;
}
[data-testid="stSidebar"] button:hover { background-color: #f0f0f0 !important; border: 1px solid #c9a876 !important; }
.main-title { font-size: 1.9rem; font-weight: 700; color: #1a1a1a; margin-bottom: 2px; }
.subtitle { color: #777; font-size: 0.95rem; margin-bottom: 1.2rem; }
[data-testid="stChatMessage"] { background-color: transparent; padding: 6px 0; }
[data-testid="stChatMessageContent"] p, [data-testid="stChatMessageContent"] li { color: #222; font-size: 0.98rem; line-height: 1.6; }
.stChatInput textarea { border-radius: 12px !important; }
.disclaimer-box {
    background-color: #fff8e6; border: 1px solid #f0dca0; border-radius: 10px;
    padding: 10px 14px; color: #8a6d1a; font-size: 0.85rem; margin-bottom: 1.2rem;
}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_pipeline():
    vectorstore = load_vectorstore()
    article_index = load_article_index()
    page_index = load_page_index()
    llm = build_llm()
    return vectorstore, article_index, page_index, llm

vectorstore, article_index, page_index, llm = get_pipeline()

with st.sidebar:
    st.markdown("### 📜 About")
    st.write(
        "Answers questions about the **Constitution of Pakistan** "
        "using its official text (27th Amendment, 2025), with article-level citations."
    )
    st.markdown("### 💡 Try asking")
    example_questions = [
        "What is Article 25 about?",
        "How can the Constitution be amended?",
        "What rights do religious minorities have?",
        "How is the Chief Justice appointed?",
    ]
    for eq in example_questions:
        if st.button(eq, use_container_width=True, key=f"ex_{eq}"):
            st.session_state.pending_question = eq
    st.markdown("---")
    st.caption("⚠️ Informational only — not legal advice.")

st.markdown('<p class="main-title">📜 Pakistan Constitution Q&A</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Ask in plain language — get cited answers from the official text.</p>', unsafe_allow_html=True)
st.markdown(
    '<div class="disclaimer-box">⚠️ This tool is informational only and is not a substitute for legal advice.</div>',
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

for msg in st.session_state.messages:
    avatar = "🧑" if msg["role"] == "user" else "📜"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

typed_question = st.chat_input("Ask about the Constitution of Pakistan...")
question = typed_question or st.session_state.pending_question
st.session_state.pending_question = None

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(question)

    with st.chat_message("assistant", avatar="📜"):
        with st.spinner("Reading the Constitution..."):
            answer, pages = answer_question(question, vectorstore, llm, article_index, page_index)
            st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()