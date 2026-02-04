# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "jinja2>=3.1.6",
#     "jsonschema>=4.26.0",
#     "spiff-arena-common==0.1.6",
#     "spiffworkflow==3.1.2",
# ]
# ///

import io
import json
import sys
import unittest

from spiff_arena_common.runner import advance_workflow, specs_from_xml

def pending_task(r):
    for p in r.get("pending_tasks", []):
        if p["task_spec"]["manual"]:
            return p

def expected_pending_task(r):
    task = pending_task(r)
    if not task or task["state"] != 32:
        return task
    stack = task["data"].get("spiff_testFixture", {}).get("pendingTaskStack", [])
    if not stack:
        return None
    expected = stack.pop()
    if task["task_spec"]["name"] != expected["id"]:
        return None
    task["data"].update(expected["data"])
    return task

def test_workflow(specs, state, completed_task):
    while True:
        r = json.loads(advance_workflow(specs, state, completed_task, "greedy", None))
        if r.get("status") != "ok" or r.get("completed"):
            break
        state = r["state"]
        completed_task = expected_pending_task(r)
        if not completed_task:
            break
    return r

###

files_by_process_id = {
    "Process_diu8ta2": "bpmn/test-cases/manual-tasks/manual_tasks.bpmn",
    "Process_1770128055928": "bpmn/test-cases/ut/ut.bpmn",
    "dict_tests": "bpmn/test-cases/dict-tests/dict-tests.bpmn",
}

def slurp(file):
    with open(file) as f:
        return f.read()

class BpmnTestCase(unittest.TestCase):
    def __init__(self, name, specs):
        self.name = name
        self.specs = specs
        self.output = ""
        self.testsRun = 0
        self.wasSuccessful = False
        super().__init__()

    def lazy_load(self, ids):
        self.specs = json.loads(self.specs)
        for id in ids:
            name = files_by_process_id[id]
            specs, err = specs_from_xml([(name, slurp(name))])
            self.assertIsNone(err)
            specs = json.loads(specs)
            subprocess_specs = self.specs["subprocess_specs"]
            subprocess_specs[id] = specs["spec"]
            subprocess_specs.update(specs["subprocess_specs"])
        self.specs = json.dumps(self.specs)

    def runTest(self):
        iters = 0
        state = {}
        while iters < 100:
            iters = iters + 1
            r = test_workflow(self.specs, state, None)
            state = r["state"]
            lazy_loads = r.get("lazy_loads")
            if not lazy_loads:
                break
            self.lazy_load(lazy_loads)
        
        self.assertEqual(r.get("status"), "ok")
        completed = r.get("completed")
        self.assertTrue(completed, f"{self.name} did not complete.")
        
        if completed:
            self.assertIn("result", r)
            data = r["result"]
        else:
            self.assertIn("pending_tasks", r)
            pending = r["pending_tasks"]
            self.assertGreater(len(pending), 0)
            self.assertIn("data", pending[0])
            data = pending[0]["data"]
        self.assertIn("spiff_testResult", data)
        result = data["spiff_testResult"]
        self.assertIn("output", result)
        self.assertIn("testsRun", result)
        self.assertIn("wasSuccessful", result)
        
        self.output = result["output"]
        self.testsRun = result["testsRun"]
        self.wasSuccessful = completed and result["wasSuccessful"]
        self.assertTrue(self.wasSuccessful)
        
if __name__ == "__main__":
    tests = []
    for name in [
        "bpmn/test-cases/dict-tests/test.bpmn",
        "bpmn/test-cases/manual-tasks/test-mt.bpmn",
        "bpmn/test-cases/ut/test.bpmn",
    ]:
        specs, err = specs_from_xml([(name, slurp(name))])
        assert not err
        tests.append(BpmnTestCase(name, specs))
    suite = unittest.TestSuite()
    suite.addTests(tests)
    stream = io.StringIO() 
    result = unittest.TextTestRunner(stream=stream).run(suite)
    output = [t.output for t in tests if not t.wasSuccessful and t.output] + [stream.getvalue()]
    print(output[0])
    sys.exit(not result.wasSuccessful())
