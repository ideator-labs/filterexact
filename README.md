# FilterExact

Agents filter memories by integer ids and timestamps. Snowflake message ids and nanosecond timestamps are above 2**53. Several popular memory stores compare those as float64, so a filter can return the neighbor of the memory you asked for, or nothing.

FilterExact is one shared set of 15 integer filters, run against real local copies of 9 store setups, with the exact answer checked by a plain Python int reference.

```
bash demo.sh           # 10 pass/fail checks, exit 0
bash demo.sh --break   # reference compares as float64, exit 1
```

Measured on 2026-11-05 (pinned versions in `demo.sh`). WRONG means a silent wrong answer.

| store | ok | WRONG | error | unsupported |
|---|---|---|---|---|
| LangGraph SqliteStore 3.1.3 | 5 | 9 | 0 | 1 |
| Chroma 1.5.9 (PersistentClient) | 11 | 4 | 0 | 0 |
| Qdrant client 1.20.0, local mode | 13 | 2 | 0 | 0 |
| Qdrant server 1.20.0, no payload index | 10 | 5 | 0 | 0 |
| Qdrant server 1.20.0, integer index | 9 | 6 | 0 | 0 |
| Qdrant server 1.20.0, integer index, raw REST with JSON integers | 9 | 6 | 0 | 0 |
| LanceDB 0.41.0 | 11 | 0 | 4 | 0 |
| Milvus Lite 3.2.2 | 15 | 0 | 0 | 0 |

One example. LangGraph `store.search(filter={"seq": 9007199254740993})` returns the record with `seq = 9007199254740992`. This is [langgraph#9607](https://github.com/langchain-ai/langgraph/issues/9607).

Another. On Qdrant, adding an integer payload index to the same data changes 7 of 15 answers. Out-of-range float bounds saturate to i64 limits. This is [qdrant#11379](https://github.com/qdrant/qdrant/issues/11379). A JSON integer bound sent straight to the REST API is still compared as a float (`seq >= 1855000000000000002` returns `...001`).

Needs `uv`, `curl` and Linux x86_64. Downloads the Qdrant release binary (sha256 pinned) and the Python packages on first run. No accounts, no network services beyond those downloads.

For the full handoff (data shape, repo map, limits, next steps) read [AGENTS.md](AGENTS.md).
