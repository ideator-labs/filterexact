import os, tempfile
from importlib.metadata import version
from pymilvus import MilvusClient
from common import FIELD, RECORDS, run

client = MilvusClient(os.path.join(tempfile.mkdtemp(), "milvus.db"))
client.create_collection("memories", dimension=2)
ids = {k: i + 1 for i, k in enumerate(RECORDS)}
keys = {i: k for k, i in ids.items()}
client.insert("memories", [{"id": ids[k], "vector": [0.1, 0.2], FIELD: v} for k, v in RECORDS.items()])
EXPR = {"eq": "==", "ne": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}


def query(case):
    v = case["value"]
    expr = f"{FIELD} in {v!r}" if case["op"] == "in" else f"{FIELD} {EXPR[case['op']]} {v!r}"
    rows = client.query("memories", filter=expr, output_fields=["id"], limit=100)
    return [keys[r["id"]] for r in rows]


run("milvus-lite", f"milvus-lite {version('milvus-lite')}, pymilvus {version('pymilvus')}", query)
