import json, os, sys

OUT = os.environ.get("FE_OUT", "results")
SPEC = json.load(open("cases.json"))
CASES = [c["id"] for c in SPEC["cases"]]
EXPECT = {c["id"]: sorted(c["expect"]) for c in SPEC["cases"]}
STORES = ["reference", "langgraph-sqlitestore", "chroma", "qdrant-local-mode",
          "qdrant-server-no-index", "qdrant-server-int-index", "qdrant-server-rest-json-int",
          "lancedb", "milvus-lite"]

runs = {}
for s in STORES:
    p = os.path.join(OUT, f"{s}.json")
    if os.path.exists(p):
        runs[s] = json.load(open(p))
oracle = {c: runs["reference"]["results"][c].get("got") for c in CASES} if "reference" in runs else {}


def verdict(r, case):
    if "unsupported" in r:
        return "unsupported"
    if "error" in r:
        return "error"
    return "ok" if r["got"] == oracle.get(case) else "WRONG"


table = {s: {c: verdict(runs[s]["results"][c], c) for c in CASES} for s in runs}
count = lambda s, v: sum(1 for c in CASES if table.get(s, {}).get(c) == v)
got = lambda s, c: runs.get(s, {}).get("results", {}).get(c, {}).get("got")

with open(os.path.join(OUT, "matrix.md"), "w") as f:
    f.write("| store | version | ok | WRONG | error | unsupported |\n|---|---|---|---|---|---|\n")
    for s in runs:
        f.write(f"| {s} | {runs[s]['version']} | {count(s,'ok')} | {count(s,'WRONG')} | {count(s,'error')} | {count(s,'unsupported')} |\n")
    f.write("\n| case | " + " | ".join(runs) + " |\n|---|" + "---|" * len(runs) + "\n")
    for c in CASES:
        f.write(f"| {c} | " + " | ".join(table[s][c] for s in runs) + " |\n")
    f.write("\nWRONG answers (got vs exact):\n")
    for s in runs:
        for c in CASES:
            if table[s][c] == "WRONG":
                f.write(f"- {s} {c}: got {got(s, c)} expected {oracle[c]}\n")

print(open(os.path.join(OUT, "matrix.md")).read())

checks = []
def check(name, ok):
    checks.append(ok)
    print(("PASS" if ok else "FAIL") + "  " + name)

check("reference store matches all 15 hand-written expectations",
      bool(oracle) and all(oracle[c] == EXPECT[c] for c in CASES))
check(f"all {len(STORES)} stores ran ({len(runs)} result files)", len(runs) == len(STORES))
check("LangGraph SqliteStore: filter seq == 2**53+1 returns the 2**53 neighbor (langgraph#9607)",
      got("langgraph-sqlitestore", "eq_2p53_1") == ["msg_2p53"])
n = count("langgraph-sqlitestore", "WRONG")
check(f"LangGraph SqliteStore silently wrong on {n} of {len(CASES)} cases (pinned: 9)", n == 9)
check("Qdrant server with integer index: seq < 1e20 drops i64_max (qdrant#11379)",
      table.get("qdrant-server-int-index", {}).get("lt_1e20") == "WRONG"
      and "i64_max" not in (got("qdrant-server-int-index", "lt_1e20") or ["i64_max"]))
diff = [c for c in CASES if got("qdrant-server-no-index", c) != got("qdrant-server-int-index", c)]
check(f"Qdrant server: same data, same filter, adding an index changes {len(diff)} answers ({', '.join(diff)})",
      len(diff) >= 1)
check("Qdrant server, raw REST with a JSON integer bound: seq >= snow_b still returns snow_a (server compares as float)",
      "snow_a" in (got("qdrant-server-rest-json-int", "gte_snow_b") or []))
n = count("chroma", "WRONG")
check(f"Chroma silently wrong on {n} of {len(CASES)} cases (pinned: 4)", n == 4)
check("control: Milvus Lite answers all 15 exactly (exact int64 filtering is possible)",
      count("milvus-lite", "ok") == len(CASES))
check(f"LanceDB fails loudly, not silently ({count('lancedb','error')} errors, 0 WRONG)",
      "lancedb" in runs and count("lancedb", "WRONG") == 0)

print(f"\n{sum(checks)}/{len(checks)} checks passed")
sys.exit(0 if all(checks) else 1)
