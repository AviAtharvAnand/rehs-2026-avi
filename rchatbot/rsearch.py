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
    state: str | None = None,
    county: str | None = None,
    service_area: str | None = None,
) -> list[dict]:
    
    query_embedding = embed(query)
    results = []

    if state and county and service_area:
        local_res = coll.query(
            query_embeddings=[query_embedding],
            n_results=8,
            where={
                "$and": [
                    {"state": state},
                    {"county": county},
                    {"service_area": service_area},
                ]
            },
        )

        results.append(local_res)

    if state and county:
        county_res = coll.query(
            query_embeddings=[query_embedding],
            n_results=4,
            where={
                "$and": [
                    {"state": state},
                    {"county": county},
                    {"location_level": "county"},
                ]
            },
        )

        results.append(county_res)

    if state:
        state_res = coll.query(
            query_embeddings=[query_embedding],
            n_results=4,
            where={
                "$and": [
                    {"state": state},
                    {"location_level": "state"},
                ]
            },
        )

        results.append(state_res)

    general_res = coll.query(
        query_embeddings=[query_embedding],
        n_results=8,
        where={"scope": "general"},
    )

    results.append(general_res)

    combined = []

    for res in results:
        for d, m, s in zip(
            res["documents"][0],
            res["metadatas"][0],
            res["distances"][0],
        ):
            combined.append({
                "text": d,
                "source_url": m["source_url"],
                "title": m["title"],
                "score": s,
                "scope": m.get("scope"),
                "state": m.get("state"),
                "county": m.get("county"),
                "service_area": m.get("service_area"),
                "location_level": m.get("location_level"),
            })

    return combined
 