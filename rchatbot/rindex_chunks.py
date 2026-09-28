import os
import json
import chromadb
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path

load_dotenv()
client = OpenAI(api_key=os.environ["NRP_LLM_TOKEN"],
                base_url=os.environ.get("NRP_LLM_BASE_URL", "https://ellm.nrp-nautilus.io/v1"))

chunks = []

for file in Path("recycling/chunks").glob("*.json"):
    with open(file, encoding="utf-8") as f:
        chunks.append(json.load(f))

def embed(text: str) -> list[float]:
    return client.embeddings.create(model="qwen3-embedding", input=[text]).data[0].embedding

def make_metadata(c):
    metadata = {
        "source_url": c["source_url"],
        "title": c["title"],
        "scope": c.get("scope"),
        "state": c.get("state"),
        "county": c.get("county"),
        "service_area": c.get("service_area"),
        "city": c.get("city"),
    }

    return {
        key: value
        for key, value in metadata.items()
        if value is not None
    }

chroma_client = chromadb.PersistentClient(path="./recycling_chroma_db")

try:
    chroma_client.delete_collection("recycling_docs")
except Exception:
    pass

coll = chroma_client.create_collection("recycling_docs")

coll.add(
    ids=[c["id"] for c in chunks],
    documents=[c["text"] for c in chunks],
    embeddings=[embed(c["text"]) for c in chunks],
    metadatas=[make_metadata(c) for c in chunks],
)

print(f"Indexed {coll.count()} chunks.")
