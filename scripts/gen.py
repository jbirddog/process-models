import json

from dataclasses import dataclass
from glob import glob
from typing import Any

from SpiffWorkflow.spiff.parser.process import SpiffBpmnParser
from SpiffWorkflow.spiff.specs.defaults import CallActivity

@dataclass
class ParsingContext:
    process_ids_by_file: dict[str, list[str]]
    file_by_process_id: dict[str, str]
    process_spec_by_id: dict[str, Any]
    called_element_ids_by_process_id: dict[str, list[str]]

def extend_called_element_ids(ctx):
    def extend(ids, resolved):
        extended = [*ids]
        for id in ids:
            if id not in resolved:
                resolved[id] = extend(ctx.called_element_ids_by_process_id.get(id, []), resolved)
            extended.extend(resolved[id])
        extended = list(set(extended))
        return extended
    resolved = {}
    for k, v in ctx.called_element_ids_by_process_id.items():
        extended = extend(v, resolved)
        ctx.called_element_ids_by_process_id[k] = extended
    
def find_called_element_ids(process_id, process_spec, ctx):
    called_element_ids = []
    for task_spec in process_spec.task_specs.values():
        if isinstance(task_spec, CallActivity):
            called_element_ids.append(task_spec.spec)
    if len(called_element_ids) > 0:
        ctx.called_element_ids_by_process_id[process_id] = called_element_ids

def parse_bpmn_file(bpmn_file, ctx):
    parser = SpiffBpmnParser()
    parser.add_bpmn_files([bpmn_file])
    process_ids = parser.get_process_ids()
    ctx.process_ids_by_file[bpmn_file] = process_ids

    for process_id in process_ids:
        if process_id in ctx.file_by_process_id:
            raise Exception(f"Duplicate process_id: {process_id}")

        process_spec = parser.get_spec(process_id, required=False)
        
        ctx.file_by_process_id[process_id] = bpmn_file
        ctx.process_spec_by_id[process_id] = process_spec
        find_called_element_ids(process_id, process_spec, ctx)
        
def generate_manifest_and_workflows(bpmn_files):
    ctx = ParsingContext(
        process_ids_by_file = {},
        file_by_process_id = {},
        process_spec_by_id = {},
        called_element_ids_by_process_id = {},
    )
    
    for bpmn_file in bpmn_files:
        parse_bpmn_file(bpmn_file, ctx)

    extend_called_element_ids(ctx)
    print(json.dumps(ctx.called_element_ids_by_process_id, sort_keys=True, indent=2))

if __name__ == "__main__":
    bpmn_files = glob("bpmn/**/*.bpmn")
    generate_manifest_and_workflows(bpmn_files)
