import bpy
from .utils import *
from . import ecs
from bpy.app.handlers import persistent
import addon_utils
import sys
import os



def _obj_component_updated(obj, smithy_component_instance):
    if smithy_component_instance.name == "Render2D" and smithy_component_instance.is_global:
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
        else:
            clear_material_image(obj)
    
def _scene_changed(old_scene, new_scene):
    old_room = old_scene.smithy2d.get_active_room()
    old_variant = old_room.get_active_variant() if old_room else None
    new_room = new_scene.smithy2d.get_active_room()
    new_variant = new_room.get_active_variant() if new_room else None
    switch_state((old_scene, old_room, old_variant), (new_scene, new_room, new_variant))

_previous_scene_id = None
_previous_scene_name = None
@persistent
def _on_depgraph_update_post(scene):
    global _previous_scene_id
    global _previous_scene_name
    if _previous_scene_id != scene.smithy2d.id:
        # TODO scene changed
        for s in bpy.data.scenes:
            if s.smithy2d.id == _previous_scene_id:
                _scene_changed(s, scene)
                break
    elif _previous_scene_name != scene.name:
        # TODO scene renamed
        pass
    _previous_scene_id = scene.smithy2d.id
    _previous_scene_name = scene.name


def register():
    ecs.add_component_updated_callback(_obj_component_updated)
    #bpy.app.handlers.depsgraph_update_post.append(_on_depgraph_update_post)

def unregister():
    #bpy.app.handlers.depsgraph_update_post.remove(_on_depgraph_update_post)
    pass