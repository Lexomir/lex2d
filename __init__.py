# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

# -----------------------------------------


bl_info = {
    "name" : "Lex2D",
    "author" : "lexomir",
    "description" : "",
    "blender" : (2, 80, 0),
    "location" : "",
    "warning" : "uh oh spaghetti-o's",
    "category" : "Scene"
}

import bpy
import sys
from bpy.app.handlers import persistent
from . import auto_load
this_module = sys.modules[__name__]
auto_load.init()

# ===========================================================
#   Interface for connecting to external modules ('lex_suite')

this_module._waiting_for_lex_suite = True

def waiting_for_module(name):
    return name == "lex_suite" and this_module.__addon_enabled__ and this_module._waiting_for_lex_suite

# connection attempted by lex_suite
def connect_module(module):
    if module.__name__ == "lex_suite":
        this_module._waiting_for_lex_suite = False
        print("Lex2D: Connected to Lex Suite")
        _lex_suite_registered(module)

# connection attempted by lex_suite
def disconnect_module(module):
    if module.__name__ == "lex_suite":
        this_module._waiting_for_lex_suite = True
        print("Lex2D: Disconnected from Lex Suite")
        _lex_suite_unregistered(module)
# ===========================================================

# trying to connect to lex_suite
def _try_connect_to_module(name):
    external_module = sys.modules.get(name)
    return external_module and external_module.request_module_connection(this_module)

def register():
    # reach out for lexsuite
    connected_to_suite = _try_connect_to_module("lex_suite")
    this_module._waiting_for_lex_suite = not connected_to_suite

def unregister():
    lexsuite = sys.modules.get('lex_suite')
    if lexsuite:
        lexsuite.request_module_disconnection(this_module)
    else:
        auto_load.unregister()

    this_module._waiting_for_lex_suite = True


_lexsuite = None
def get_lexsuite():
    global _lexsuite
    if _lexsuite:
        return _lexsuite
    else:
        _lexsuite = sys.modules.get('lex_suite')
        return _lexsuite

_lex_suite_callbacks = []
def add_lex_suite_registered_callback(callback):
    _lex_suite_callbacks.append(callback)


@persistent
def _on_blend_load_post(dummy):
    # adapt old data into new version
    for obj in bpy.data.objects:
        if obj.lexgame.smithy.script_components:
            for old_c in obj.lexgame.smithy.script_components:
                c = obj.smithy2d.add_component(old_c.filepath)
                for old_i in old_c.inputs:
                    i = c.inputs.get(old_i.name)
                    i._set_string_value(old_i.get_string())
                    i.set_meta(old_i.datatype, old_i.get_args())
            obj.lexgame.smithy.script_components.clear()
    for sc in bpy.data.scenes:
        if sc.lexsm.node_group:
            sc.smithy2d.statemachine_name = sc.lexsm.node_group.strip()
            sc.lexsm.node_group = ""
    
    out_of_date_node_editors = [area for screen in bpy.data.screens for area in screen.areas if area.type == "NODE_EDITOR" and area.spaces.active.tree_type == 'LexSM_SceneNodeTree']
    for area in out_of_date_node_editors:
        area.spaces.active.tree_type = 'Smithy2D_SM_SceneNodeTree'

    groups = [ng for ng in bpy.data.node_groups if type(ng).__name__ == "LexSM_SceneNodeTree"]
    for old_ng in groups:
        nodegroup_name = old_ng.name
        new_ng = bpy.data.node_groups.new(nodegroup_name, 'Smithy2D_SM_SceneNodeTree')
        for old_n in old_ng.nodes:
            n = None
            if type(old_n).__name__ == "LexSM_SceneStateNode":
                n = new_ng.nodes.new("Smithy2D_SM_SceneStateNode")
                n.outputs.clear()
                for old_output in old_n.outputs:
                    n.outputs.new('Smithy2D_SM_StateSocket', old_output.name)
                for old_s in old_n.object_states:
                    # copy from old state
                    s = n.object_states.add()
                    s.name = old_s.name
                    for old_sc in old_s.smithy_components_serialized:
                        if old_sc.filepath:
                            sc = s.components_serialized.add()
                            sc.filepath = old_sc.filepath
                            sc.data = old_sc.data
                    for old_data in old_s.custom_state_data:
                        new_data = s.custom_state_data.add()
                        new_data.name = old_data.name
                        new_data.value = old_data.value
                    s.location = old_s.location
                    s.rotation_quaternion = old_s.rotation_quaternion
                    s.scale = old_s.scale
                    s.dimensions = old_s.dimensions
            else:
                n = new_ng.nodes.new(type(old_n).__name__)
            n.name = old_n.name
            n.location = old_n.location
            n.width = old_n.width
        for old_n in old_ng.nodes:
            for output_i, output in enumerate(old_n.outputs):
                for link in output.links:
                    n = new_ng.nodes.get(old_n.name)
                    to_node = new_ng.nodes.get(link.to_node.name)
                    new_ng.links.new(to_node.inputs[-1], n.outputs[output_i])

        # get any lexsm_nodetree node editor space and change to smithy2d_nodetree
        for area in out_of_date_node_editors:
            area_nodetree = area.spaces.active.node_tree
            if area_nodetree and area_nodetree == old_ng:
                area.spaces.active.node_tree = new_ng
        
        bpy.data.node_groups.remove(old_ng)
        new_ng.name = nodegroup_name

def _lex_suite_registered(lex_suite_module):
    global _lex_suite
    _lex_suite = lex_suite_module
    
    auto_load.register()
    print("Registered Lex2D")

    for cb in _lex_suite_callbacks:
        cb(lex_suite_module)

    bpy.app.handlers.load_post.append(_on_blend_load_post)

    # each object, copy lexgame.smithy.script_components to smithy2d.components
    # each scene, copy lexsm.group_node to smithy2d.statemachine_name
    # each lexsm_nodetree, make a smithy2d tree with same name, copy nodes 
    # any screen space with lexsm_nodetree replace with smithy2d_nodetree

def _lex_suite_unregistered(lex_suite_module):
    bpy.app.handlers.load_post.remove(_on_blend_load_post)
    auto_load.unregister()
