# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "jinja2>=3.1.6",
#     "jsonschema>=4.26.0",
#     "spiff-arena-common==0.1.7",
#     "spiffworkflow==3.1.2",
# ]
# ///

import io
import json
import os
import sys
import unittest

from collections import namedtuple

from spiff_arena_common.runner import advance_workflow, specs_from_xml

class BpmnTestCase(unittest.TestCase):
    def __init__(self, file, specs, specs_by_id):
        self.file = file
        self.specs = specs
        self.specs_by_id = specs_by_id
        self.state = {}
        self.output = ""
        self.testsRun = 0
        self.wasSuccessful = False
        super().__init__()

    def lazy_load(self, ids):
        self.specs = json.loads(self.specs)
        for id in ids:
            specs = json.loads(self.specs_by_id[id])
            subprocess_specs = self.specs["subprocess_specs"]
            subprocess_specs[id] = specs["spec"]
            subprocess_specs.update(specs["subprocess_specs"])
        self.specs = json.dumps(self.specs)

    def runTest(self):
        iters = 0
        while iters < 100:
            iters = iters + 1
            r = json.loads(advance_workflow(self.specs, self.state, None, "unittest", None))
            self.state = r["state"]
            lazy_loads = r.get("lazy_loads")
            if not lazy_loads:
                break
            self.lazy_load(lazy_loads)
        
        self.assertEqual(r.get("status"), "ok")
        completed = r.get("completed")
        
        if completed:
            self.assertIn("result", r)
            data = r["result"]
        else:
            self.assertIn("pending_tasks", r)
            pending = r["pending_tasks"]
            self.assertGreater(len(pending), 0)
            self.assertIn("data", pending[0])
            data = pending[0]["data"]

        stack = data.get("spiff_testFixture", {}).get("pendingTaskStack", [])
        self.assertEqual(stack, [])
        
        self.assertIn("spiff_testResult", data)
        result = data["spiff_testResult"]
        self.assertIn("output", result)
        self.assertIn("testsRun", result)
        self.assertIn("wasSuccessful", result)
        
        self.output = result["output"]
        self.testsRun = result["testsRun"]
        self.wasSuccessful = completed and result["wasSuccessful"]
        self.assertTrue(self.wasSuccessful)

###

def files_to_parse(dir):
    for root, dirs, files in os.walk(dir, topdown=True):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        yield from [os.path.join(root, f) for f in files if f.endswith(".bpmn")] # TODO: dmn

def slurp(file):
    with open(file) as f:
        return f.read()

Test = namedtuple("Test", ["file", "specs"])
TestCtx = namedtuple("TestCtx", ["files", "specs", "tests"])
TestCov = namedtuple("TestCov", ["all", "completed", "missing"])
Tally = namedtuple("Tally", ["completed", "all", "percent"])
CovTally = namedtuple("CovTally", ["result", "breakdown"])

def index(dir):
    ctx = TestCtx([], {}, [])
    for file in files_to_parse(dir):
        specs, err = specs_from_xml([(file, slurp(file))])
        assert not err
        if file.endswith("_test.bpmn"):
            ctx.tests.append(Test(file, specs))
        else:
            d = json.loads(specs)
            id = d["spec"]["name"]
            assert id not in ctx.specs
            ctx.files.append((id, file))
            ctx.specs[id] = specs
    ctx.files.sort(key=lambda f: f[1])
    ctx.tests.sort()
    return ctx

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
    ctx = index(".")
    test_cases = []
    for t in ctx.tests:
        test_cases.append(BpmnTestCase(t.file, t.specs, ctx.specs))
    suite = unittest.TestSuite()
    suite.addTests(test_cases)
    stream = io.StringIO() 
    result = unittest.TextTestRunner(stream=stream).run(suite)    
    output = [t.output for t in test_cases if not t.wasSuccessful and t.output] + [stream.getvalue()]
    print(output[0])

    if not result.wasSuccessful():
        sys.exit(1)

    print("Unit Test Task Coverage:\n")
    
    cov, tally = task_coverage(ctx.specs, [t.state for t in test_cases])
    for id, f in ctx.files:
        [completed, all, percent] = tally.breakdown[id]
        print(f"{f} - {completed}/{all} - {percent:.2f}%")
    
    [completed, all, percent] = tally.result
    print(f"\nTotal - {completed}/{all} - {percent:.2f}%")

    if percent < 10.0:
        sys.exit(1)
