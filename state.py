import bpy
from .utils import *
from . import ecs
from .properties import SMITHY2D_INVALID_ID
from bpy.app.handlers import persistent
import addon_utils
import sys
import os



def _obj_component_updated(scene, obj, smithy_component_instance):
    if smithy_component_instance.name == "Render2D" and smithy_component_instance.is_global:
        rel_img_filepath = smithy_component_instance.get_input('asset')
        if rel_img_filepath:
            abs_img_filepath = os.path.join(get_image_dir(), rel_img_filepath)

            for ext in ['.png', '.jpg']:
                if os.path.exists(bpy.path.abspath(abs_img_filepath + ext)):
                    print("Setting object '{}' texture to '{}'".format(obj.name, rel_img_filepath))
                    mat = get_or_create_image_material(rel_img_filepath + ext) #, tile_size=tile_size)
                    assign_material_to_object(obj, mat)
                    break
        else:
            clear_material_image(obj)

def register():
    ecs.add_component_updated_callback(_obj_component_updated)

def unregister():
    ecs.remove_component_updated_callback(_obj_component_updated)