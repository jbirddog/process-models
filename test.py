# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "jinja2>=3.1.6",
#     "jsonschema>=4.26.0",
#     "spiff-arena-common @/home/jon/dev/spiff-arena/dist/spiff_arena_common-0.1.9-py3-none-any.whl",
#     "spiffworkflow==3.1.2",
# ]
# ///

import json
import sys

from spiff_arena_common.coverage import task_coverage
from spiff_arena_common.data_stores import JSONFileDataStore, JSONFileDataStoreConverter
from SpiffWorkflow.spiff.serializer.config import SPIFF_CONFIG

class JSONFileDataStoreDelegate:
    def get(self, bpmn_id, my_task):
        with open(f"examples/{bpmn_id}.json") as f:
            data = json.loads(f.read())
        return data, None
    def set(self, bpmn_id, my_task, data):
        with open(f"examples/{bpmn_id}.json", "w") as f:
            f.write(json.dumps(data))
        return None

class MyJSONFileDataStoreConverter(JSONFileDataStoreConverter):
    def from_dict(self, dct):
        ds = super().from_dict(dct)
        ds.delegate = JSONFileDataStoreDelegate()
        return ds

SPIFF_CONFIG[JSONFileDataStore] = MyJSONFileDataStoreConverter

from spiff_arena_common.tester import run_tests_in_dir

if __name__ == "__main__":
    ctx, result, output = run_tests_in_dir(".")
    output = [t.output for t in ctx.test_cases if not t.wasSuccessful and t.output] + [output]
    print(output[0])

    if not result.wasSuccessful():
        sys.exit(1)

    print("Unit Test Task Coverage:\n")
    
    cov, tally = task_coverage(ctx)
    for id, f in ctx.files:
        completed, all, percent = tally.breakdown[id]
        print(f"{f} - {completed}/{all} - {percent:.2f}%")
    
    completed, all, percent = tally.result
    print(f"\nTotal - {completed}/{all} - {percent:.2f}%")

    if percent < 20.0:
        sys.exit(1)
