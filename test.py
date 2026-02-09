# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "jinja2>=3.1.6",
#     "jsonschema>=4.26.0",
#     "spiff-arena-common==0.1.8",
#     "spiffworkflow==3.1.2",
# ]
# ///

import sys

from spiff_arena_common.coverage import task_coverage
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
