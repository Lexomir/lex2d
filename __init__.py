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
    "version" : (1, 0, 0),
    "location" : "",
    "warning" : "uh oh spaghetti-o's",
    "category" : "Scene"
}

import bpy
import os
import uuid
import sys
from .utils import *
from mathutils import Vector, Matrix, Quaternion
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
def _on_blend_save_pre(context):
    for bpy_scene in bpy.data.scenes:
        bpy_scene.smithy2d.version = get_addon_version()


@persistent
def _on_blend_load_post(dummy):
    if bpy.data.filepath:
        # write the "last_opened_state_info.txt" file (TODO: why do i need this??)
        if bpy.context.scene.smithy2d.scenes:
            serialized_state = ""
            for scene in bpy.context.scene.smithy2d.scenes:
                serialized_state += "{}~\n".format(serialize_scene(scene))
            state_outputfilepath = os.path.join(bpy.path.abspath("//"), ".lexeditor", "last_opened_state_info.txt")
            os.makedirs(os.path.dirname(state_outputfilepath), exist_ok=True)
            with open(state_outputfilepath, "w") as state_file:
                state_file.write(serialized_state)
    
        # check version
        version_on_file = bpy.context.scene.smithy2d.version
        current_version = get_addon_version()
        if addon_has_breaking_changes(version_on_file, current_version):
            bpy.ops.smithy2d.update_assets_to_addon_version("INVOKE_DEFAULT", old_version=version_on_file, new_version=current_version)

        # sync with the assets on drive
        bpy.ops.smithy2d.sync_with_asset_folder()

    for im in bpy.data.images:
        im.colorspace_settings.name = "sRGB"
            

def _lex_suite_registered(lex_suite_module):
    global _lex_suite
    _lex_suite = lex_suite_module
    
    auto_load.register()
    print("Registered Lex2D")

    for cb in _lex_suite_callbacks:
        cb(lex_suite_module)

    bpy.app.handlers.load_post.append(_on_blend_load_post)
    bpy.app.handlers.save_pre.append(_on_blend_save_pre)


def _lex_suite_unregistered(lex_suite_module):
    bpy.app.handlers.load_post.remove(_on_blend_load_post)
    bpy.app.handlers.save_pre.remove(_on_blend_save_pre)
    auto_load.unregister()
