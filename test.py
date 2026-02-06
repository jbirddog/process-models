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

files_by_process_id = {
    "Process_diu8ta2": "bpmn/test-cases/manual-tasks/manual_tasks.bpmn",
    "Process_1770128055928": "bpmn/test-cases/ut/ut.bpmn",
    "dict_tests": "bpmn/test-cases/dict-tests/dict-tests.bpmn",
    "coin-gecko_simple-price": "bpmn/test-cases/http-v2-connector-test/httpv2.bpmn",
}

def slurp(file):
    with open(file) as f:
        return f.read()

class BpmnTestCase(unittest.TestCase):
    def __init__(self, name, specs):
        self.name = name
        self.specs = specs
        self.state = {}
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

TestCtx = namedtuple("TestCtx", ["specs", "tests"])
        
def index(dir):
    ctx = TestCtx({}, [])
    for file in files_to_parse(dir):
        specs, err = specs_from_xml([(file, slurp(file))])
        assert not err
        ctx.specs[file] = specs
        if file.endswith("_test.bpmn"):
            ctx.tests.append(file)
    return ctx

###
        
if __name__ == "__main__":
    ctx = index(".")
    print(ctx.tests)
    sys.exit(0)
    tests = []
    for name in [
        "bpmn/test-cases/dict-tests/test.bpmn",
        "bpmn/test-cases/manual-tasks/test-mt.bpmn",
        "bpmn/test-cases/ut/test.bpmn",
        "bpmn/test-cases/http-v2-connector-test/test_get.bpmn",
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
