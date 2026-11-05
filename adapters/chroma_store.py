import tempfile
import chromadb
from common import FIELD, RECORDS, run

col = chromadb.PersistentClient(path=tempfile.mkdtemp()).create_collection("memories")
col.add(ids=list(RECORDS), embeddings=[[0.1, 0.2]] * len(RECORDS),
        metadatas=[{FIELD: v} for v in RECORDS.values()])


def query(case):
    return col.get(where={FIELD: {"$" + case["op"]: case["value"]}})["ids"]


run("chroma", chromadb.__version__, query)
