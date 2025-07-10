import os
import requests
import faiss
import pickle
import json
import pandas as pd
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("LM_API_URL") or "http://localhost:1234/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "local-model"

# Global vector index & doc storage
pdf_chunks = {}  # filename -> [chunks]
pdf_indexes = {}  # filename -> FAISS index
tabular_data = []  # Flattened rows from CSV/Excel

embedder = SentenceTransformer('all-MiniLM-L6-v2')

SYSTEM_PROMPT = """You are a helpful equipment troubleshooting assistant. 
You help with industrial issues like motor faults, PLC errors, HMI problems, sensor diagnostics, etc. 
Provide actionable and step-by-step advice based on the uploaded documentation or logs.
"""

# ---------------- PDF Ingestion -------------------
def ingest_pdf(path, name="default"):
    reader = PdfReader(path)
    full_text = "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
    chunks = [full_text[i:i+500] for i in range(0, len(full_text), 500)]
    embeddings = embedder.encode(chunks)

    index = faiss.IndexFlatL2(len(embeddings[0]))
    index.add(embeddings)

    pdf_chunks[name] = chunks
    pdf_indexes[name] = index

    # Optionally save to disk
    with open(f"chunks_{name}.pkl", "wb") as f:
        pickle.dump(chunks, f)
    faiss.write_index(index, f"index_{name}.faiss")

# ---------------- CSV/Excel Ingestion -------------------
def ingest_csv_or_excel(path):
    ext = path.split(".")[-1]
    df = pd.read_csv(path) if ext == "csv" else pd.read_excel(path)
    for _, row in df.iterrows():
        row_text = " | ".join([f"{col}: {val}" for col, val in row.items()])
        tabular_data.append(row_text)

# ---------------- Context Chunk Lookup -------------------
def get_relevant_chunks(query, top_k=3):
    results = []
    for name, index in pdf_indexes.items():
        if name in pdf_chunks:
            query_vec = embedder.encode([query])
            D, I = index.search(query_vec, top_k)
            matched = [pdf_chunks[name][i] for i in I[0]]
            results.extend(matched)

    # Add tabular matches
    for row in tabular_data:
        if any(token.lower() in row.lower() for token in query.lower().split()):
            results.append(row)

    return "\n\n".join(results[:top_k * 2])

# ---------------- Summarization -------------------
def summarize_text(query):
    context = get_relevant_chunks(query)
    prompt = f"Summarize the following text:\n\n{context}"
    return query_local_llm(prompt)

# ---------------- Query - Non Streaming -------------------
def query_local_llm(prompt, history=None):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages += history
    context = get_relevant_chunks(prompt)
    messages.append({"role": "user", "content": f"{context}\n\nQ: {prompt}"})

    try:
        response = requests.post(
            f"{API_URL}/chat/completions",
            json={"model": MODEL_NAME, "messages": messages, "temperature": 0.7},
            timeout=30
        )
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error: {str(e)}"

# ---------------- Streaming from Local LLM -------------------
def stream_response_from_llm(prompt, history=None):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages += history
    context = get_relevant_chunks(prompt)
    messages.append({"role": "user", "content": f"{context}\n\nQ: {prompt}"})

    try:
        response = requests.post(
            f"{API_URL}/chat/completions",
            json={
                "model": MODEL_NAME,
                "messages": messages,
                "temperature": 0.7,
                "stream": True,
            },
            stream=True,
            timeout=60,
        )

        for line in response.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                content = line.removeprefix("data: ")
                if content == "[DONE]":
                    break
                try:
                    token = json.loads(content)["choices"][0]["delta"].get("content", "")
                    yield token
                except:
                    continue
    except Exception as e:
        yield f"\n[Stream error: {str(e)}]"
