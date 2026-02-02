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

    def runTest(self):
        r = json.loads(advance_workflow(self.specs, {}, None, "greedy", None))
        self.assertIn("status", r)
        self.assertEqual(r["status"], "ok")
        self.assertIn("completed", r)
        self.assertTrue(r["completed"])
        self.assertIn("result", r)
        self.assertIn("test_result", r["result"])
        result = r["result"]["test_result"]
        self.output = result["output"]
        self.testsRun = result["testsRun"]
        self.wasSuccessful = result["wasSuccessful"]
        self.assertTrue(self.wasSuccessful)

cases = {
    "tests/basic-example.bpmn": [
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
    output = io.StringIO() 
    result = unittest.TextTestRunner(stream=output).run(suite)

    for t in tests:
        if not t.wasSuccessful:
            print(t.output)

    wasSuccessful = result.wasSuccessful()
    if wasSuccessful:
        print(output.getvalue())
    sys.exit(not wasSuccessful)
