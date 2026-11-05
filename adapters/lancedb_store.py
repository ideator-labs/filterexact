import tempfile
import lancedb, pyarrow as pa
from common import FIELD, RECORDS, run

db = lancedb.connect(tempfile.mkdtemp())
table = db.create_table("memories", pa.table({
    "key": list(RECORDS),
    FIELD: pa.array(list(RECORDS.values()), pa.int64()),
    "vector": [[0.1, 0.2]] * len(RECORDS),
}))
SQL = {"eq": "=", "ne": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}


def query(case):
    v = case["value"]
    where = f"{FIELD} IN ({', '.join(map(repr, v))})" if case["op"] == "in" else f"{FIELD} {SQL[case['op']]} {v!r}"
    return list(table.search().where(where).limit(100).to_arrow()["key"].to_pylist())


run("lancedb", lancedb.__version__, query)
