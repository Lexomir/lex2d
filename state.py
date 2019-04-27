import bpy
from .utils import *
from bpy.app.handlers import persistent
import addon_utils
import sys
import os



def _obj_component_updated(obj, smithy_component_instance):
    if smithy_component_instance.filepath == "Render2D":
        rel_img_filepath = smithy_component_instance.get_input('asset')
        if rel_img_filepath:
            abs_img_filepath = os.path.join(get_image_dir(), rel_img_filepath)

            for ext in ['.png', '.jpg']:
                if os.path.exists(bpy.path.abspath(abs_img_filepath + ext)):
                    spritesheet_data = find_spritesheet_data_for_image(rel_img_filepath + ext)
                    tile_size = spritesheet_data['tile_size'] if spritesheet_data else None
                    mat, tex_node = set_material_image_texture(obj, abs_img_filepath + ext, tile_size=tile_size)
                    image = tex_node.image
                    tile_size = tile_size or image.size

                    # Regenerate mesh data
                    bm = create_rectangle_bmesh(screen_to_bl_size(tile_size))
                    apply_bmesh_to_object(obj, bm)
                    bm.free()
                    break
    


@persistent
def _on_lex_suite_registered(lex_suite):
    lex_suite.lex_game.smithy.add_component_updated_callback(_obj_component_updated)

def register():
    from . import add_lex_suite_registered_callback
    add_lex_suite_registered_callback(_on_lex_suite_registered)


def unregister():
    pass