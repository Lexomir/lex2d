import bpy
from .utils import *
from bpy.app.handlers import persistent
import addon_utils
import sys
import os



def _obj_component_updated(obj, smithy_component_instance):
    if smithy_component_instance.filepath == "Renderer2D":
        rel_spritesheet_filepath = smithy_component_instance.get_input('asset')
        if rel_spritesheet_filepath:
            spritesheet_filepath = get_image_dir() + rel_spritesheet_filepath

            for ext in ['.png', '.jpg']:
                if os.path.exists(bpy.path.abspath(spritesheet_filepath + ext)):
                    set_material_image_texture(obj, spritesheet_filepath + ext, tile_size=smithy_component_instance.get_input('tile_size'))
                    break
    


@persistent
def _on_lex_suite_registered(lex_suite):
    lex_suite.lex_game.smithy.add_component_updated_callback(_obj_component_updated)

def register():
    print("Registered Lex2D")
    add_lex_suite_registered_callback(_on_lex_suite_registered)


def unregister():
    pass