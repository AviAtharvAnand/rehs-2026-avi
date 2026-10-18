import chromadb
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CHROMA_PATH = BASE_DIR / "recycling_chroma_db"

coll = (
    chromadb.PersistentClient(path=str(CHROMA_PATH))
    .get_collection("recycling_docs")
)

general = coll.get(
    where={"scope": "general"},
    include=["metadatas"]
)

print("General chunks in Chroma:", len(general["ids"]))

local = coll.get(
    where={
        "$and": [
            {"state": "Nevada"},
            {"county": "Clark"},
            {"service_area": "Las Vegas Henderson"},
        ]
    },
    include=["metadatas"]
)

print("Las Vegas Henderson chunks:", len(local["ids"]))

