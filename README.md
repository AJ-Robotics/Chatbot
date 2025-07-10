# Offline AI Chatbot for Equipment Troubleshooting

Streamlit-based chatbot using a local LLM via LM Studio for industrial equipment diagnostics.

## Features
- ChatGPT-like UI
- Local LLM (Mistral, LLaMA3, etc. via LM Studio)
- Equipment-specific prompt tuning
- PDF/manual ingestion with vector search
- Fully offline capable

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start LM Studio (http://localhost:1234) with a chat model

3. Run:
```bash
streamlit run chatbot.py
```

4. Upload a manual in sidebar and start asking equipment-related queries.
