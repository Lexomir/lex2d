import bpy
import os
from ..utils import abs_state_scriptpath
import sys
from bpy.app.handlers import persistent

def register():
    lexsuite = sys.modules.get('lex_suite')
    globals()['FileWatcher'] = lexsuite.filewatcher.FileWatcher

    bpy.app.handlers.frame_change_post.append(_frame_change_post)

def unregister():
    bpy.app.handlers.frame_change_post.remove(_frame_change_post)

_state_filewatchers = {}
def get_or_create_filewatcher(state_node):
    abs_filepath = abs_state_scriptpath(state_node.name)
    return _state_filewatchers.setdefault(state_node.name, FileWatcher(abs_filepath))


def parse_state_script(abs_filepath):
    if os.path.exists(abs_filepath):
        outputs = []
        with open(abs_filepath, "r") as state_file:
            for line in state_file:
                output_prefix = "--$"
                if line[:len(output_prefix)] == output_prefix:
                    output_str = line[len(output_prefix):].strip()
                    outputs.append(output_str)
                else: 
                    break    
        return outputs
    else:
        return ["Continue", "Nah"]


def on_update():
    nodegroup = bpy.context.scene.smithy2d.get_statemachine()

    if not nodegroup:
        return

    for state in nodegroup.nodes:
        state_fw = get_or_create_filewatcher(state)
        if state_fw.look():
            # reparse script for node outputs
            parsed_outputs = parse_state_script(state_fw.filename)

            while len(state.outputs) < len(parsed_outputs):
                node_output = state.outputs.new('Smithy2D_SM_StateSocket', output_name)
            while len(state.outputs) > len(parsed_outputs):
                state.outputs.remove(state.outputs[-1])
            
            # rename the outputs
            for i, output_name in enumerate(parsed_outputs): 
                state.outputs[i].name = output_name

@persistent
def _frame_change_post(scene):
    on_update()
