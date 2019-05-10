# import bpy
# import os
# from ..utils import *
# import sys
# from bpy.app.handlers import persistent

# def register():
#     lexsuite = sys.modules.get('lex_suite')
#     globals()['FileWatcher'] = lexsuite.filewatcher.FileWatcher

#     bpy.app.handlers.frame_change_post.append(_frame_change_post)

# def unregister():
#     bpy.app.handlers.frame_change_post.remove(_frame_change_post)

# _state_filewatchers = {}
# def get_or_create_filewatcher(state_node):
#     abs_filepath = asset_abspath(room_script_assetpath(state_node.name))
#     return _state_filewatchers.setdefault(state_node.name, FileWatcher(abs_filepath))


# def parse_room_script(abs_filepath):
#     if os.path.exists(abs_filepath):
#         outputs = []
#         with open(abs_filepath, "r") as state_file:
#             for line in state_file:
#                 output_prefix = "--$"
#                 if line[:len(output_prefix)] == output_prefix:
#                     output_str = line[len(output_prefix):].strip()
#                     outputs.append(output_str)
#                 else: 
#                     break    
#         return outputs
#     else:
#         return ["Continue", "Nah"]


# def on_update():
#     pass

# @persistent
# def _frame_change_post(scene):
#     on_update()
