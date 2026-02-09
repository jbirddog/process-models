# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "jinja2>=3.1.6",
#     "jsonschema>=4.26.0",
#     "spiff-arena-common @/home/jon/dev/spiff-arena/dist/spiff_arena_common-0.1.8-py3-none-any.whl",
#     "spiffworkflow==3.1.2",
# ]
# ///

import json
import sys
import unittest

from collections import namedtuple

from spiff_arena_common.tester import run_tests_in_dir

###

TestCov = namedtuple("TestCov", ["all", "completed", "missing"])
Tally = namedtuple("Tally", ["completed", "all", "percent"])
CovTally = namedtuple("CovTally", ["result", "breakdown"])

def cov_tasks(states):
    for state in states:
        for _, sp in state["subprocesses"].items():
            id = sp["spec"]
            for _, task in sp["tasks"].items():
                if task["state"] == 64:
                    yield id, task["task_spec"]

def tally(cov):
    completed = 0
    all = 0
    breakdown = {}
    for id in cov.all:
        c = len(cov.completed[id])
        a = len(cov.all[id])
        breakdown[id] = Tally(c, a, c / a * 100)
        completed += c
        all += a
    result = Tally(completed, all, completed / all * 100)
    return CovTally(result, breakdown)

def task_coverage(specs, states):
    all = {}
    completed = {}
    missing = {}
    for id, task_id in cov_tasks(states):
        if id not in completed:
            completed[id] = set()
        completed[id].add(task_id)
    for id, spec in specs.items():
        if id not in completed:
            completed[id] = set()
        spec = json.loads(spec)["spec"]
        all[id] = set([t for t in spec["task_specs"]])
        missing[id] = all[id] - completed[id]

    cov = TestCov(all, completed, missing)
    return cov, tally(cov) 

###

if __name__ == "__main__":
    [ctx, result, output] = run_tests_in_dir(".")
    output = [t.output for t in ctx.test_cases if not t.wasSuccessful and t.output] + [output]
    print(output[0])

    if not result.wasSuccessful():
        sys.exit(1)

    print("Unit Test Task Coverage:\n")
    
    cov, tally = task_coverage(ctx.specs, [t.state for t in ctx.test_cases])
    for id, f in ctx.files:
        [completed, all, percent] = tally.breakdown[id]
        print(f"{f} - {completed}/{all} - {percent:.2f}%")
    
    [completed, all, percent] = tally.result
    print(f"\nTotal - {completed}/{all} - {percent:.2f}%")

    if percent < 20.0:
        sys.exit(1)
