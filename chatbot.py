import streamlit as st
import time
import os
from playsound import playsound
import threading

from llm_client import (
    stream_response_from_llm,
    ingest_pdf,
    ingest_csv_or_excel,
    summarize_text,
)
from utils import init_session, add_message, reset_conversation

# App config
st.set_page_config(page_title="💀 Equipment AI Terminal", layout="wide")

# Hacker-style UI
st.markdown("""
    <style>
    html, body, [class*="css"]  {
        background-color: #0d0d0d !important;
        color: #00FF00 !important;
        font-family: 'Courier New', monospace !important;
    }
    .stTextInput, .stTextArea, .stFileUploader, .stButton, .stCheckbox, .stSelectbox, .stDownloadButton {
        background-color: #1a1a1a !important;
        color: #00FF00 !important;
        border: 1px solid #00FF00 !important;
    }
    .user-bubble, .bot-bubble {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
        max-width: 90%;
        font-family: 'Courier New', monospace;
        font-size: 15px;
        white-space: pre-wrap;
    }
    .user-bubble {
        background-color: #003300;
        color: #00FF00;
        align-self: flex-end;
        border: 1px solid #00FF00;
    }
    .bot-bubble {
        background-color: #000000;
        color: #00FF00;
        align-self: flex-start;
        border: 1px solid #00FF00;
    }
    .chat-container {
        display: flex;
        flex-direction: column;
    }
    .stMarkdown h2, .stMarkdown p {
        color: #00FF00 !important;
    }
    .stSidebar {
        background-color: #0d0d0d !important;
    }
    </style>
""", unsafe_allow_html=True)

# Enable arrow key navigation via JavaScript
st.markdown("""
    <script>
    let history = [];
    let index = 0;

    document.addEventListener('keydown', function(e) {
        const inputBox = window.parent.document.querySelector('textarea');
        if (!inputBox) return;

        if (e.key === 'ArrowUp') {
            if (index > 0) {
                index -= 1;
                inputBox.value = history[index];
                inputBox.dispatchEvent(new Event('input', { bubbles: true }));
            }
        } else if (e.key === 'ArrowDown') {
            if (index < history.length - 1) {
                index += 1;
                inputBox.value = history[index];
                inputBox.dispatchEvent(new Event('input', { bubbles: true }));
            } else {
                inputBox.value = "";
            }
        } else if (e.key === 'Enter') {
            if (inputBox.value.trim()) {
                history.push(inputBox.value);
                index = history.length;
            }
        }
    });
    </script>
""", unsafe_allow_html=True)

# Init session state
init_session()

# Sidebar
with st.sidebar:
    st.markdown("Equipment AI Terminal", unsafe_allow_html=True)
    uploaded_pdfs = st.file_uploader("Upload Manuals (PDF)", type="pdf", accept_multiple_files=True)
    if uploaded_pdfs:
        os.makedirs("manuals", exist_ok=True)
        for pdf in uploaded_pdfs:
            path = f"manuals/{pdf.name}"
            with open(path, "wb") as f:
                f.write(pdf.read())
            ingest_pdf(path, pdf.name)
        st.success(f"Ingested {len(uploaded_pdfs)} manuals")

    uploaded_csv = st.file_uploader("Upload CSV / Excel Logs", type=["csv", "xlsx"])
    if uploaded_csv:
        os.makedirs("tables", exist_ok=True)
        path = f"tables/{uploaded_csv.name}"
        with open(path, "wb") as f:
            f.write(uploaded_csv.read())
        ingest_csv_or_excel(path)
        st.success("Log data ingested")

    st.button("🔁 Reset Chat", on_click=reset_conversation)
    st.session_state.summarize_mode = st.checkbox("🧠 Summarize Mode (manuals)")

# Title
st.markdown("""
    <h2 style='color: #00FF00;'>🤖 EQUIPMENT AI CHATBOT</h2>
    <p style='color: #00FF00;'>Ask about faults, PID tuning, motor issues, or summarize manuals.</p>
""", unsafe_allow_html=True)

# Chat history
for role, content in st.session_state.chat_log:
    css_class = "user-bubble" if role == "user" else "bot-bubble"
    align = "flex-end" if role == "user" else "flex-start"
    st.markdown(f"<div class='chat-container' style='align-items: {align};'>"
                f"<div class='{css_class}'>{content}</div></div>", unsafe_allow_html=True)

# Chat input
if prompt := st.chat_input(">> Ask your question or command..."):
    add_message("user", prompt)
    st.markdown(f"<div class='chat-container' style='align-items: flex-end;'>"
                f"<div class='user-bubble'>{prompt}</div></div>", unsafe_allow_html=True)

    full_response = ""
    placeholder = st.empty()

    def play_click():
        try:
            playsound("assets/type.wav", block=False)
        except:
            pass

    if st.session_state.summarize_mode or prompt.lower().startswith("summarize"):
        summary = summarize_text(prompt)
        full_response = summary
        placeholder.markdown(f"<div class='chat-container' style='align-items: flex-start;'>"
                             f"<div class='bot-bubble'>{summary}</div></div>", unsafe_allow_html=True)
    else:
        with placeholder.container():
            stream_area = st.empty()
            for chunk in stream_response_from_llm(prompt, st.session_state.history):
                full_response += chunk
                stream_area.markdown(
                    f"<div class='chat-container' style='align-items: flex-start;'>"
                    f"<div class='bot-bubble'>{full_response}_</div></div>",
                    unsafe_allow_html=True
                )
                threading.Thread(target=play_click).start()
                time.sleep(0.01)

    add_message("assistant", full_response)
