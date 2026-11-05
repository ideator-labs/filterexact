import json, sys, tempfile, urllib.request
from importlib.metadata import version
from qdrant_client import QdrantClient, models as M
from common import FIELD, RECORDS, run

mode = sys.argv[1]
if mode == "local":
    client, name = QdrantClient(path=tempfile.mkdtemp()), "qdrant-local-mode"
else:
    client = QdrantClient(url=sys.argv[2])
    name = {"server-no-index": "qdrant-server-no-index", "server-index": "qdrant-server-int-index",
            "server-rest": "qdrant-server-rest-json-int"}[mode]

ids = {k: i + 1 for i, k in enumerate(RECORDS)}
keys = {i: k for k, i in ids.items()}
if client.collection_exists("memories"):
    client.delete_collection("memories")
client.create_collection("memories", vectors_config=M.VectorParams(size=2, distance=M.Distance.COSINE))
if mode in ("server-index", "server-rest"):
    client.create_payload_index("memories", FIELD, M.PayloadSchemaType.INTEGER, wait=True)
client.upsert("memories", [M.PointStruct(id=ids[k], vector=[0.1, 0.2], payload={FIELD: v})
                           for k, v in RECORDS.items()], wait=True)


def rest_scroll(flt):
    """Sends the filter as raw JSON so integer bounds reach the server as JSON integers."""
    req = urllib.request.Request(f"{sys.argv[2]}/collections/memories/points/scroll",
                                 data=json.dumps({"filter": flt, "limit": 100}).encode(),
                                 headers={"Content-Type": "application/json"})
    return [keys[p["id"]] for p in json.load(urllib.request.urlopen(req))["result"]["points"]]


def rest_query(op, v):
    if op == "eq":
        return rest_scroll({"must": [{"key": FIELD, "match": {"value": v}}]})
    if op == "ne":
        return rest_scroll({"must_not": [{"key": FIELD, "match": {"value": v}}]})
    if op == "in":
        return rest_scroll({"must": [{"key": FIELD, "match": {"any": v}}]})
    return rest_scroll({"must": [{"key": FIELD, "range": {op: v}}]})


def query(case):
    op, v = case["op"], case["value"]
    if mode == "server-rest":
        return rest_query(op, v)
    if op == "eq":
        flt = M.Filter(must=[M.FieldCondition(key=FIELD, match=M.MatchValue(value=v))])
    elif op == "ne":
        flt = M.Filter(must_not=[M.FieldCondition(key=FIELD, match=M.MatchValue(value=v))])
    elif op == "in":
        flt = M.Filter(must=[M.FieldCondition(key=FIELD, match=M.MatchAny(any=v))])
    else:
        flt = M.Filter(must=[M.FieldCondition(key=FIELD, range=M.Range(**{op: v}))])
    points, _ = client.scroll("memories", scroll_filter=flt, limit=100)
    return [keys[p.id] for p in points]


server = "" if mode == "local" else f" server {client.info().version}"
run(name, f"client {version('qdrant-client')}{server}", query)
client.close()
