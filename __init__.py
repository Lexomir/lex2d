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
    for o in bpy.data.objects:
        render2d_c = o.smithy2d.get_component("Render2D")
        if render2d_c:
            asset_path = render2d_c.get_input("asset")
            render2d_c.set_input('asset', asset_path.replace('\\', '/'))
            

def _lex_suite_registered(lex_suite_module):
    global _lex_suite
    _lex_suite = lex_suite_module
    
    auto_load.register()
    print("Registered Lex2D")

    for cb in _lex_suite_callbacks:
        cb(lex_suite_module)

    bpy.app.handlers.load_post.append(_on_blend_load_post)


def _lex_suite_unregistered(lex_suite_module):
    bpy.app.handlers.load_post.remove(_on_blend_load_post)
    auto_load.unregister()
