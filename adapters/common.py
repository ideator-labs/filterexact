import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = json.load(open(os.path.join(HERE, "..", "cases.json")))
FIELD = SPEC["field"]
RECORDS = SPEC["records"]
CASES = SPEC["cases"]


class Unsupported(Exception):
    pass


def run(store, version, query):
    """query(case) returns a list of record keys. Unsupported means the store has no such operator."""
    results = {}
    for case in CASES:
        try:
            results[case["id"]] = {"got": sorted(query(case))}
        except Unsupported as e:
            results[case["id"]] = {"unsupported": str(e)}
        except Exception as e:
            results[case["id"]] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    out = {"store": store, "version": version, "results": results}
    path = os.path.join(os.environ.get("FE_OUT", "results"), f"{store}.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    print(f"  ran {store} {version}")
