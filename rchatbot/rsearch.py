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

BASE_DIR = Path(__file__).resolve().parent
CHROMA_PATH = BASE_DIR / "recycling_chroma_db"

coll = chromadb.PersistentClient(path=str(CHROMA_PATH)).get_or_create_collection("recycling_docs")

def search(
    query: str,
    k: int = 5,
    state: str | None = None,
    county: str | None = None,
) -> list[dict]:

    where = None

    if state and county:
        where = {
            "$or": [
                {
                    "$and": [
                        {"state": state},
                        {"county": county}
                    ]
                },
                {"scope": "general"}
            ]
        }

    elif state:
        where = {
            "$or": [
                {"state": state},
                {"scope": "general"}
            ]
        }
    
    res = coll.query(query_embeddings=[embed(query)], n_results=k, where=where)
    return [
        {
            "text": d,
            "source_url": m["source_url"],
            "title": m["title"],
            "score": s,
            "scope": m.get("scope"),
            "state": m.get("state"),
            "county": m.get("county"),
        }
        for d, m, s in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
    ]
 