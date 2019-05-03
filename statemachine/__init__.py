'''
Depends on lex_editor and lex_game
'''
import bpy

_obj_save_callbacks = []
_obj_load_callbacks = []
def add_object_save_callback(func):
    _obj_save_callbacks.append(func)

def add_object_load_callback(func):
    _obj_load_callbacks.append(func)


_scene_save_callbacks = []
_scene_load_callbacks = []
def add_scene_save_callback(func):
    _scene_save_callbacks.append(func)
    
def add_scene_load_callback(func):
    _scene_load_callbacks.append(func)


_scene_state_created_callbacks = []
def add_scene_state_created_callback(cb):
    _scene_state_created_callbacks.append(cb)

_scene_state_namechange_callbacks = []
def add_scene_state_namechange_callback(cb):
    _scene_state_namechange_callbacks.append(cb)


def get_statemachine(name):
    from .node_base import Smithy2D_SM_BaseNodeTree
    nodegroup = bpy.data.node_groups.get(name)
    return nodegroup if isinstance(nodegroup, Smithy2D_SM_BaseNodeTree) else None