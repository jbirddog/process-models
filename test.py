# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "jinja2>=3.1.6",
#     "jsonschema>=4.26.0",
#     "spiff-arena-common==0.1.6",
#     "spiffworkflow==3.1.2",
# ]
# ///

from spiff_arena_common.runner import advance_workflow, specs_from_xml

cases = {
    "tests/basic-example.bpmn": [
        "bpmn/test-cases/dict-tests/dict-tests.bpmn",
    ],
}

def slurp(file):
    with open(file) as f:
        return f.read()

def main():
    for t, deps in cases.items():
        files = [(t, slurp(t))] + [(d, slurp(d)) for d in deps]
        specs, err = specs_from_xml(files)
        r = advance_workflow(specs, {}, None, "greedy", None)

if __name__ == "__main__":
    main()
