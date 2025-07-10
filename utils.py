import streamlit as st

def init_session():
    if "chat_log" not in st.session_state:
        st.session_state.chat_log = []
    if "history" not in st.session_state:
        st.session_state.history = []
    if "summarize_mode" not in st.session_state:
        st.session_state.summarize_mode = False

def add_message(role, content):
    st.session_state.chat_log.append((role, content))
    if role in ["user", "assistant"]:
        st.session_state.history.append({"role": role, "content": content})

def reset_conversation():
    st.session_state.chat_log = []
    st.session_state.history = []
    st.session_state.summarize_mode = False
