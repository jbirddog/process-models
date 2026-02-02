# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "jinja2>=3.1.6",
#     "jsonschema>=4.26.0",
#     "spiff-arena-common==0.1.6",
#     "spiffworkflow==3.1.2",
# ]
# ///

import json
import sys
import unittest

from spiff_arena_common.runner import advance_workflow, specs_from_xml

class BpmnTestCase(unittest.TestCase):
    def __init__(self, specs):
        self.specs = specs
        super().__init__()

    def runTest(self):
        r = json.loads(advance_workflow(self.specs, {}, None, "greedy", None))
        assert r["status"] == "ok"
        assert r["completed"]
        test_result = r["result"]["test_result"]
        assert test_result["failures"] == 0

cases = {
    "tests/basic-example.bpmn": [
        "bpmn/test-cases/dict-tests/dict-tests.bpmn",
    ],
}

def slurp(file):
    with open(file) as f:
        return f.read()
        
if __name__ == "__main__":
    suite = unittest.TestSuite()
    for t, deps in cases.items():
        files = [(t, slurp(t))] + [(d, slurp(d)) for d in deps]
        specs, err = specs_from_xml(files)
        assert not err
        suite.addTest(BpmnTestCase(specs))
    result = unittest.TextTestRunner().run(suite)
    sys.exit(not result.wasSuccessful())
