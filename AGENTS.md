# AGENTS.md

Handoff for a coding agent with no prior context.

## What this is

FilterExact is a conformance suite for metadata filters in agent memory stores. It targets one failure. Integer ids and timestamps above 2**53 (Discord or X style snowflake ids, nanosecond epoch timestamps, i64 sequence numbers) get compared as float64. The store then returns a neighbor memory, drops the right one, or saturates an out-of-range bound.

The claim. On pinned current releases, LangGraph SqliteStore, Chroma and Qdrant (local mode and server) return silently wrong rows for plain integer filters. Milvus Lite answers every case exactly, so exact int64 filtering is a choice, not a limit of vector stores.

## Status

Real:
- Every store is the real released package or binary, run locally. LangGraph `langgraph-checkpoint-sqlite` 3.1.3, `chromadb` 1.5.9, `qdrant-client` 1.20.0 local mode, the Qdrant 1.20.0 server release binary, `lancedb` 0.41.0, `milvus-lite` 3.2.2 with `pymilvus` 3.0.2.
- The expected answers are written by hand in `cases.json`, then checked against a plain Python int reference.

Stubbed:
- Vectors are a constant `[0.1, 0.2]`. Only metadata filtering is under test. No embedding model runs.

Not covered: Mem0, Letta, Graphiti, pgvector, Weaviate, PGlite, Postgres-backed LangGraph stores.

## Data shape

`cases.json`:
- `field`: the metadata key, `seq`.
- `records`: key to i64 value. 9 records. Two at 2**53 and 2**53+1, two consecutive snowflakes, two timestamps 1 ns apart, i64 max, i64 min, 1.
- `cases`: 15 entries `{id, op, value, expect}`. `op` is one of `eq ne gt gte lt lte in`. `value` is a JSON integer, or a float like `1e20` for the out-of-range cases. `expect` is the sorted list of matching record keys.

Each adapter writes `results/<store>.json`:
`{"store", "version", "results": {case_id: {"got": [keys]} | {"error": msg} | {"unsupported": msg}}}`.

`check.py` turns those into verdicts per case: `ok`, `WRONG` (silent wrong rows vs the reference), `error` (store raised), `unsupported` (store has no such operator). It writes `results/matrix.md` and runs the checks.

## Repo map

- `demo.sh` is the artifact. It fetches the pinned Qdrant binary into `.cache/`, starts it on port 16333 (override with `QDRANT_PORT`), runs every adapter in its own `uv run --with ...` env, then `check.py`.
- `cases.json` holds records, filters and hand-written expectations.
- `adapters/common.py` loads `cases.json` and runs every case through a store's `query(case)` function.
- `adapters/reference.py` is the exact Python int oracle. `FE_BREAK=1` makes it compare as float64.
- `adapters/langgraph_sqlite.py`, `chroma_store.py`, `qdrant_store.py` (modes `local`, `server-no-index`, `server-index`, `server-rest`), `lancedb_store.py`, `milvus_store.py` are one adapter per store.
- `check.py` builds the matrix and the 10 checks. Stdlib only.

## Setup, run, verify (fresh clone)

```
git clone https://github.com/ideator-labs/filterexact
cd filterexact
bash demo.sh; echo "exit=$?"
```

Expected: the last line before exit is `10/10 checks passed` and `exit=0`. First run downloads about 34 MB for Qdrant and the Python wheels. Later runs take about 15 s.

```
bash demo.sh --break; echo "exit=$?"
```

Expected: `5/10 checks passed`, `exit=1`. The reference now compares as float64, the same bug the stores have. Its answers no longer match `cases.json`, LangGraph and Chroma counts move off their pinned values, and the Milvus Lite and LanceDB controls look wrong against the broken oracle.

Requires: Linux x86_64, `uv`, `curl`, `python3`, `sha256sum`. No Docker.

## Design decisions

- Python adapters, because every store under test ships a Python client and these are the clients agent frameworks use. Each adapter runs in its own pinned `uv` env so versions cannot drift together.
- The Qdrant server is the real release binary, not Docker. Docker is not installed on the build box.
- The `server-rest` mode posts raw JSON so integer bounds reach the server as JSON integers. It separates client coercion (`qdrant_client.models.Range` fields are `float`) from server behavior. Both are wrong.
- Verdicts compare against the reference run, not only `cases.json`. That way `--break` shows what happens when the oracle itself has the bug.
- LangGraph checks and Chroma checks pin the exact WRONG counts (9 and 4). A fixed release should fail the check, and that is the signal to update the pin and the README table.
- An adapter file must not share a name with a package it imports. `milvus_lite.py` shadowed the `milvus_lite` package and broke Milvus Lite with a misleading "milvus-lite is required" error.

## Known limits

- One field, one type (i64). No floats, bools, strings, dates or arrays yet.
- Qdrant local mode and the server get the same filter models, so their WRONG cases differ only where index paths differ.
- Milvus Lite uses its dynamic JSON field (the quick-start path). An explicit INT64 schema field is not tested.
- LanceDB rejects float bounds on an int64 column with an error. That is counted as `error`, not wrong. Whether it should coerce is a design call.
- The suite does not test persistence or restart. All stores are freshly loaded each run.
- Results are from one run on one box (2026-11-05). Pins will go stale as stores fix bugs.

## Next steps

1. Add Mem0 OSS through its SQLite history and a local vector store. Done when `results/mem0-*.json` exists and `matrix.md` has its row.
2. Add an explicit INT64 schema field for Milvus Lite and a typed column for Chroma if offered. Done when both Milvus modes appear in the matrix.
3. Add a float, bool and string type round (e.g. `1 == true`, `"10" == 10`). Done when `cases.json` has a `type_cases` block and every adapter reports a verdict for it.
4. Add a restart round: write, close, reopen, filter. Done when each persistent store has a `*-reopen` row with the same verdicts or a recorded difference.
5. Publish `results/matrix.md` per release in CI. Done when a GitHub Actions run uploads the matrix as an artifact.

## Working rules

- `bash demo.sh` must end in `exit=0` on a clean clone before any commit. `bash demo.sh --break` must exit 1.
- Pin every package and binary version. Update the README table only from a real run.
- Do not post on upstream issues from this repo's automation. Upstream comments go through Daniel.
- Commit as `danielgerlag <daniel@gerlag.ca>`.

## Context and sources

- [langgraph#9607](https://github.com/langchain-ai/langgraph/issues/9607). SQLite store integer filters return adjacent values above 2**53 (opened 2026-11-05).
- [qdrant#11379](https://github.com/qdrant/qdrant/issues/11379). Integer range filters wrong when float bounds are outside i64 (opened 2026-11-03).
- [chroma#7991](https://github.com/chroma-core/chroma/issues/7991). Empty metadata arrays silently dropped, another metadata type bug (opened 2026-11-03).
- [mem0#7810](https://github.com/mem0ai/mem0/issues/7810). A non-string `created_at` breaks every read for that user (opened 2026-11-01).
- LangGraph's own code comment says it converts to float "to handle inf, -inf, nan, and very large integers" (`langgraph/store/sqlite/base.py`, `_get_filter_condition`, 3.1.3).
