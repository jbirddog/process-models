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

class BpmnTestCase(unittest.TestCase):
    def __init__(self, specs):
        self.specs = specs
        self.output = ""
        self.testsRun = 0
        self.wasSuccessful = False
        super().__init__()

    def parseWorkflowResult(self, r):
        completed = r.get("completed", False)
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

    def runTest(self):
        r = json.loads(advance_workflow(self.specs, {}, None, "greedy", None))
        self.assertIn("status", r)
        self.assertEqual(r["status"], "ok")
        self.parseWorkflowResult(r)

cases = {
    "bpmn/test-cases/dict-tests/test.bpmn": [
        "bpmn/test-cases/dict-tests/dict-tests.bpmn",
    ],
}

def slurp(file):
    with open(file) as f:
        return f.read()
        
if __name__ == "__main__":
    tests = []
    for t, deps in cases.items():
        files = [(t, slurp(t))] + [(d, slurp(d)) for d in deps]
        specs, err = specs_from_xml(files)
        assert not err
        tests.append(BpmnTestCase(specs))
    suite = unittest.TestSuite()
    suite.addTests(tests)
    stream = io.StringIO() 
    result = unittest.TextTestRunner(stream=stream).run(suite)
    output = [t.output for t in tests if not t.wasSuccessful and t.output] + [stream.getvalue()]
    print(output[0])
    sys.exit(not result.wasSuccessful())
