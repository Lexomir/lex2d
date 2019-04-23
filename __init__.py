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
# depends on:
#   lex_suite.lexgame
#   lex_suite.lex_statemachine

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
from . import auto_load
this_module = sys.modules[__name__]

auto_load.init()

# ===========================================================
#   Interface for connecting to external modules ('lex_suite')

this_module._waiting_for_lex_suite = True

def waiting_for_module(name):
    return name == "lex_suite" and this_module._waiting_for_lex_suite

# connection attempted by lex_suite
def connect_module(module):
    if module.__name__ == "lex_suite":
        this_module._waiting_for_lex_suite = False
        print("Lex2D: Connected to Lex Suite")
        _lex_suite_registered(module)

# ===========================================================

# trying to connect to lex_suite
def _try_connect_to_module(name):
    external_module = sys.modules.get(name)
    return external_module and external_module.request_module_connection(this_module)

def register():
    auto_load.register()
    print("Registered Lex2D")

    # reach out for lexsuite
    connected_to_suite = _try_connect_to_module("lex_suite")
    this_module._waiting_for_lex_suite = not connected_to_suite

def unregister():
    auto_load.unregister()


_lex_suite = None
def get_lex_suite():
    global _lex_suite
    if _lex_suite:
        return _lex_suite
    else:
        _lex_suite = sys.modules.get('lex_suite')
        return _lex_suite

_lex_suite_callbacks = []
def add_lex_suite_registered_callback(callback):
    _lex_suite_callbacks.append(callback)

def _lex_suite_registered(lex_suite_module):
    global _lex_suite
    _lex_suite = lex_suite_module
    
    for cb in _lex_suite_callbacks:
        cb(lex_suite_module)
