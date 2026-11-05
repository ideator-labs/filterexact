import operator, os
from common import RECORDS, run

OPS = {"eq": operator.eq, "ne": operator.ne, "gt": operator.gt, "gte": operator.ge,
       "lt": operator.lt, "lte": operator.le}
BREAK = os.environ.get("FE_BREAK") == "1"


def num(v):
    return float(v) if BREAK else v


def query(case):
    if case["op"] == "in":
        wanted = [num(v) for v in case["value"]]
        return [k for k, v in RECORDS.items() if num(v) in wanted]
    op = OPS[case["op"]]
    return [k for k, v in RECORDS.items() if op(num(v), num(case["value"]))]


run("reference", "float64-coercion (--break)" if BREAK else "exact python int", query)
