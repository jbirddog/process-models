import json
import os
import shutil

from dataclasses import dataclass
from glob import glob
from typing import Any

from SpiffWorkflow.bpmn.serializer.workflow import BpmnWorkflowSerializer
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.spiff.parser.process import SpiffBpmnParser
from SpiffWorkflow.spiff.serializer.config import SPIFF_CONFIG
from SpiffWorkflow.spiff.specs.defaults import CallActivity

registry = BpmnWorkflowSerializer.configure(SPIFF_CONFIG)
serializer = BpmnWorkflowSerializer(registry=registry)

@dataclass
class ParsingContext:
    process_ids_by_bpmn_file: dict[str, list[str]]
    bpmn_file_by_process_id: dict[str, str]
    process_spec_by_id: dict[str, Any]
    called_element_ids_by_process_id: dict[str, list[str]]
    process_id_by_json_file: dict[str, str]

def extend_called_element_ids(ctx):
    resolved = {}
    def extend(ids):
        extended = [*ids]
        for id in ids:
            if id not in resolved:
                resolved[id] = extend(ctx.called_element_ids_by_process_id.get(id, []))
            extended.extend(resolved[id])
        return list(set(extended))
    
    for k, v in ctx.called_element_ids_by_process_id.items():
        extended = extend(v)
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
    ctx.process_ids_by_bpmn_file[bpmn_file] = process_ids

    for process_id in process_ids:
        if process_id in ctx.bpmn_file_by_process_id:
            raise Exception(f"Duplicate process_id: {process_id}")

        process_spec = parser.get_spec(process_id, required=False)
        
        ctx.bpmn_file_by_process_id[process_id] = bpmn_file
        ctx.process_spec_by_id[process_id] = process_spec
        find_called_element_ids(process_id, process_spec, ctx)

def spec_json_filename(bpmn_file, i, specs_dir):
    suffix = f"_{i}" if i > 0 else ""
    common_path = bpmn_file[4:-5]
    return f"{specs_dir}{common_path}{suffix}.json"

def serialize_workflow_specs_for_process_id(process_id, ctx):
    process = ctx.process_spec_by_id[process_id]
    called_element_ids = ctx.called_element_ids_by_process_id.get(process_id, [])
    subprocesses = {id: ctx.process_spec_by_id[id] for id in called_element_ids}
    workflow = BpmnWorkflow(process, subprocesses)
    workflow_dct = serializer.to_dict(workflow)
    workflow_specs_dct = {
        "serializer_version": "jbirddog/process-models",
        "spec": workflow_dct["spec"],
        "subprocess_specs": workflow_dct["subprocess_specs"],
    }
    return json.dumps(workflow_specs_dct, sort_keys=True, indent=2)

def generate_workflow_specs(specs_dir, ctx):
    try:
        shutil.rmtree(specs_dir)
    except FileNotFoundError:
        pass

    def write_file(filename, contents):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            f.write(contents)

    for bpmn_file, process_ids in ctx.process_ids_by_bpmn_file.items():
        for i, process_id in enumerate(process_ids):
            filename = spec_json_filename(bpmn_file, i, specs_dir)
            workflow_specs_json = serialize_workflow_specs_for_process_id(process_id, ctx)
            write_file(filename, workflow_specs_json)
            ctx.process_id_by_json_file[filename] = process_id

def generate_manifest(ctx):
    manifest = {
        "bpmn_file_by_process_id": ctx.bpmn_file_by_process_id,
        "called_element_ids_by_process_id": ctx.called_element_ids_by_process_id,
        "process_id_by_workflow_spec_json": ctx.process_id_by_json_file,
        "process_ids_by_bpmn_file": ctx.process_ids_by_bpmn_file,
    }

    with open("manifest.json", "w") as f:
        f.write(json.dumps(manifest, sort_keys=True, indent=2))
    
def generate_manifest_and_workflow_specs(bpmn_files, specs_dir):
    ctx = ParsingContext(
        process_ids_by_bpmn_file = {},
        bpmn_file_by_process_id = {},
        process_spec_by_id = {},
        called_element_ids_by_process_id = {},
        process_id_by_json_file = {},
    )
    
    for bpmn_file in bpmn_files:
        parse_bpmn_file(bpmn_file, ctx)

    extend_called_element_ids(ctx)
    generate_workflow_specs(specs_dir, ctx)
    generate_manifest(ctx)

if __name__ == "__main__":
    bpmn_files = glob("bpmn/**/*.bpmn")
    generate_manifest_and_workflow_specs(bpmn_files, "specs")
