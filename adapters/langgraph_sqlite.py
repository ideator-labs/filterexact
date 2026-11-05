import os, tempfile
from importlib.metadata import version
from langgraph.store.sqlite import SqliteStore
from common import FIELD, RECORDS, Unsupported, run

path = os.path.join(tempfile.mkdtemp(), "store.db")
with SqliteStore.from_conn_string(path) as store:
    store.setup()
    for k, v in RECORDS.items():
        store.put(("memories",), k, {FIELD: v})

    def query(case):
        if case["op"] == "in":
            raise Unsupported("SqliteStore filter has no $in")
        f = case["value"] if case["op"] == "eq" else {"$" + case["op"]: case["value"]}
        return [i.key for i in store.search(("memories",), filter={FIELD: f}, limit=100)]

    run("langgraph-sqlitestore", version("langgraph-checkpoint-sqlite"), query)
