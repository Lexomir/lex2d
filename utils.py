import bpy
import sys
import shutil
import os
import bmesh
from mathutils import Vector
import time

def refresh_screen_area(area_type):
    if bpy.context.screen:
        for area in bpy.context.screen.areas:
            if area.type == area_type:
                area.tag_redraw()
    else:
        for screen in bpy.data.screens:
            for area in screen.areas:
                if area.type == area_type:
                    area.tag_redraw()

def multiply_vec3(vec, other_vec):
    return Vector([vec[0] * other_vec[0], vec[1] * other_vec[1], vec[2] * other_vec[2]])

def divide_vec3(vec, other_vec):
    return Vector([vec[0] / other_vec[0], vec[1] / other_vec[1], vec[2] / other_vec[2]])

def move_directory(src_dir, dst_dir):
    shutil.move(src_dir, dst_dir)

class InvalidDeleteException(Exception):
    pass

def archive_and_delete_asset(assetpath):
    invalid_paths = ["scripts", "\\", "", "scripts\\core"]
    abspath = asset_abspath(assetpath)
    if os.path.normpath(assetpath.lower()) in invalid_paths:
        raise InvalidDeleteException("Cannot delete path '{}' you maniac".format(abspath))
    
    archive_abspath = asset_archive_abspath(assetpath)
    print("Archiving asset at path '{}' to '{}'".format(abspath, archive_abspath))
    if not os.path.exists(abspath):
        print("ERROR: Tried to archive path '{}' but it does not exist".format(abspath))
        return

    os.makedirs(os.path.dirname(archive_abspath), exist_ok=True)
    lock_filepath = os.path.join(abspath, ".lock") if os.path.isdir(abspath) else abspath
    with open(lock_filepath, "w"):
        if os.path.isdir(abspath):
            merge_overwrite(abspath, archive_abspath, exceptions=['.lock'])
    if os.path.isdir(abspath):
        shutil.rmtree(abspath)
    else:
        shutil.move(abspath, archive_abspath)

#recursively merge two folders including subfolders
def merge_overwrite(root_src_dir, root_dst_dir, exceptions=[]):
    for src_dir, dirs, files in os.walk(root_src_dir):
        dst_dir = src_dir.replace(root_src_dir, root_dst_dir, 1)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        for file_ in files:
            if file_ not in exceptions:
                src_file = os.path.join(src_dir, file_)
                dst_file = os.path.join(dst_dir, file_)
                if os.path.exists(dst_file):
                    os.remove(dst_file)
                shutil.copy(src_file, dst_dir)

def move_merge_folders(root_src_dir, root_dst_dir):
    merge_overwrite(root_src_dir, root_dst_dir)
    remove_dir(root_src_dir)

def remove_dir(target_dir):
    os.system('rmdir /S /Q "{}"'.format(target_dir))

def find_map_editor_areas():
    map_editors = []
    if bpy.context.screen:
        for area in bpy.context.screen.areas:
            if (area.type == "IMAGE_EDITOR" 
                and area.spaces.active.image
                and area.spaces.active.image.smithy2d.is_map):
                map_editors.append(area)
    return map_editors

def get_or_create_object(obj_name, obj_type):
    obj = bpy.data.objects.get(obj_name)
    if not obj or obj.type != obj_type:
        data = None
        if obj_type == "MESH":
            data = bpy.data.meshes.new(obj_name)
        print("Cant find '{}' so making it".format(obj_name))
        obj = bpy.data.objects.new(obj_name, data)
    return obj

def is_backstage(obj):
    backstage = bpy.data.collections.get("Backstage")
    return backstage and obj.name in backstage.objects 

def move_backstage(obj):
    if obj.name in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.unlink(obj)
    for c in bpy.data.collections:
        if obj.name in c.objects:
            c.objects.unlink(obj)

    backstage = bpy.data.collections.get("Backstage")
    if not backstage:
        backstage = bpy.data.collections.new("Backstage")
    if not "Backstage" in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(backstage)

    backstage.hide_viewport = True
    backstage.objects.link(obj)

def move_onstage(obj):
    backstage = bpy.data.collections.get("Backstage")
    if backstage and obj.name in backstage.objects:
        backstage.objects.unlink(obj)
    
    onstage = bpy.data.collections.get("OnStage")
    if not onstage:
        onstage = bpy.data.collections.new("OnStage")
    if not "OnStage" in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(onstage)

    if obj.name not in onstage.objects:
        onstage.objects.link(obj)

def save_state(state):
    scene, room, variant = state
    # save variant
    variant.save_scene_state(bpy.context.scene)
    # save map
    map_editors = find_map_editor_areas()
    map_image = map_editors[0].spaces.active.image if map_editors else None
    if map_image:
        scene.map_image = map_image.name

def load_state(state):
    scene, room, variant = state
    
    # load map
    map_editors = find_map_editor_areas()
    new_map_image = scene.get_map_image()
    if new_map_image:
        for me in map_editors:
            me.spaces.active.image = new_map_image
    # load the new variant
    variant.load_scene_state(bpy.context.scene)

def switch_state(old_state, new_state):
    old_scene, old_room, old_variant = old_state
    scene, room, variant = new_state

    def name(item):
        return item.name if item else "_"
    print("Switching from {}:{}:{} to {}:{}:{}".format(
        name(old_scene), name(old_room), name(old_variant), 
        name(scene), name(room), name(variant)))
    
    if old_variant:
        assert old_scene and old_room
        save_state(old_state)

    # if switching rooms, remove all room-local components
    if old_room != room and not room:
        for obj in bpy.context.scene.objects:
            for i, c in reversed(list(enumerate(obj.smithy2d.components))):
                if not c.is_global:
                    obj.smithy2d.components.remove(i)

    # load the new variant
    if (variant):
        assert scene and room
        load_state(new_state)

    if room:
        scene.set_room(room.index())
        if variant:
            room.set_variant(variant.index())
    
    refresh_screen_area("PROPERTIES")
    refresh_screen_area("IMAGE_EDITOR")


def set_active_material_output(my_node):
    nodes = my_node.id_data.nodes
    for node in nodes :
        if node.type == 'OUTPUT_MATERIAL' :
            node.is_active_output = False
    my_node.is_active_output = True

def get_active_material_output(nodes):   
    for node in nodes :
        if node.type == 'OUTPUT_MATERIAL' and node.is_active_output :
            return node
    for node in nodes :
        if node.type == 'OUTPUT_MATERIAL' :
            return node

def find_texture_node_with_image(nodes, image):
    for node in nodes:
        if node.type == 'TEX_IMAGE' and node.image == image:
            return node

def apply_bmesh_to_object(obj, bm):
    active_obj = bpy.context.window.view_layer.objects.active
    bpy.context.window.view_layer.objects.active = obj
    mode = bpy.context.mode
    bpy.ops.object.mode_set(mode='OBJECT')
    bm.to_mesh(obj.data)
    bpy.ops.object.mode_set(mode=mode)
    bpy.context.window.view_layer.objects.active = active_obj

def get_or_create_texture_node(nodes, image):
    for node in nodes:
        if node.type == 'TEX_IMAGE' and node.image == image and node.image.colorspace_settings.name == 'sRGB':
            return node
    node = nodes.new("ShaderNodeTexImage")
    node.image = image
    node.image.colorspace_settings.name = 'sRGB'
    return node

def get_or_create_node(nodes, node_classname):
    for node in nodes:
        if type(node).__name__ == node_classname:
            return node
    node = nodes.new(node_classname)
    return node

def get_or_create_input_node(node_tree, src_node, input_node_type, from_output_name, to_input_id):
    connected_node = None
    src_input = src_node.inputs[to_input_id]
    if src_input.links:
        connected_node = src_input.links[0].from_node
    if connected_node and type(connected_node).__name__ != input_node_type:
        connected_node = None
        node_tree.links.remove(src_input.links[0])

    if not connected_node:
        connected_node = node_tree.nodes.new(input_node_type)
        node_tree.links.new(src_input, connected_node.outputs[from_output_name])
    
    return connected_node

def find_item_idx(bpy_collection, item):
    for idx, i in enumerate(bpy_collection):
        if i == item:
            return idx
    return -1

def remove_all_except(bpy_collection, exceptions):
    for item in bpy_collection:
        if item not in exceptions:
            bpy_collection.remove(item)

def set_material_image_texture(obj, image_filepath, tile_size=None):
    # import image file
    image = bpy.data.images.load(bpy.path.relpath(image_filepath), check_existing=True)

    material = bpy.data.materials.get(obj.name)
    if not material:
        material = bpy.data.materials.new(obj.name)
    material.use_nodes = True
    material.blend_method = 'CLIP'

    mat_output = get_active_material_output(material.node_tree.nodes)

    # start from scratch if the output isnt connected to an emission node
    if mat_output.inputs['Surface'].links and type(mat_output.inputs['Surface'].links[0].from_node).__name__ != "ShaderNodeMixShader":
        remove_all_except(material.node_tree.nodes, [mat_output])

    mix_node = get_or_create_input_node(material.node_tree, mat_output, "ShaderNodeMixShader", "Shader", "Surface")
    emission_node = get_or_create_input_node(material.node_tree, mix_node, "ShaderNodeEmission", "Emission", 2)
    transparent_node = get_or_create_input_node(material.node_tree, mix_node, "ShaderNodeBsdfTransparent", "BSDF", 1)

    texture_node = get_or_create_texture_node(material.node_tree.nodes, image=image)
    material.node_tree.links.new(emission_node.inputs["Color"], texture_node.outputs["Color"])
    material.node_tree.links.new(mix_node.inputs[0], texture_node.outputs['Alpha'])

    # connect a mapping node (to only display one tile of the texture)
    tile_size = tile_size or image.size
    mapping_node = get_or_create_node(material.node_tree.nodes, "ShaderNodeMapping")
    material.node_tree.links.new(texture_node.inputs["Vector"], mapping_node.outputs["Vector"])
    tex_coord_node = get_or_create_input_node(material.node_tree, mapping_node, "ShaderNodeTexCoord", "UV", "Vector")

    mapping_node.vector_type = "TEXTURE"
    tile_count_x = round(image.size[0] / tile_size[0], 3)
    tile_count_y = round(image.size[1] / tile_size[1], 3)

    # set scale
    if bpy.app.version >= (2, 82, 0):
        mapping_node.inputs[3].default_value[0] = tile_count_x
        mapping_node.inputs[3].default_value[1] = tile_count_y
    else:
        mapping_node.scale[0] = tile_count_x
        mapping_node.scale[1] = tile_count_y

    # Assign it to object
    if obj.data.materials:
        # assign to 1st material slot
        obj.data.materials[0] = material
    else:
        # no slots
        obj.data.materials.append(material)
    
    return material, texture_node

def clear_material_image(obj):
    material = bpy.data.materials.get(obj.name)
    if not material:
        material = bpy.data.materials.new(obj.name)
    material.use_nodes = True
    material.blend_method = 'CLIP'

    mat_output = get_active_material_output(material.node_tree.nodes)
    color_node = get_or_create_input_node(material.node_tree, mat_output, 'ShaderNodeRGB', "Color", "Surface")
    color_node.outputs[0].default_value = [0.500000, 0.037542, 0.279409, 1.000000]

    # Assign it to object
    if obj.data.materials:
        # assign to 1st material slot
        obj.data.materials[0] = material
    else:
        # no slots
        obj.data.materials.append(material)
    
    return material

def get_material_image(obj):
    material = obj.data.materials[0] if obj.data.materials else None

    if not material:
        return None
    
    mat_output_node = get_active_material_output(material.node_tree.nodes)
    tex_node = find_connected_texture_node(mat_output_node)

    if tex_node and tex_node.image:
        return bpy.path.relpath(tex_node.image.filepath)
    
    return None

def find_spritesheet_data_for_image(image_filepath):
    # find spritesheet file
    abs_image_filepath = bpy.path.abspath(get_image_dir() + image_filepath)
    abs_image_dir = os.path.dirname(abs_image_filepath)
    abs_spritesheet_filepath = os.path.join(abs_image_dir, "definitions", "spritesheets.txt")

    rel_image_filepath = os.path.relpath(abs_image_filepath, start=bpy.path.abspath(get_asset_dir()))
    try:
        with open(abs_spritesheet_filepath, "r") as spritesheet_file:
            for line in spritesheet_file:
                line_parts = line.split(" ")
                referenced_image_rel_filepath = line_parts[2]
                if line_parts[0] == 'png_sheet' and os.path.normcase(referenced_image_rel_filepath) == os.path.normcase(rel_image_filepath):
                    try: tile_size = (int(line_parts[3]), int(line_parts[4]))
                    except: return None

                    return {"tile_size": tile_size}
    except FileNotFoundError:
        return None
    except: 
        print('Unhandled error: %s' % sys.exc_info()[0])
        return None

def rectangle_mesh_data(size):
    # vertices
    points = [
        (0.0, -size[1], 0.0), # BL
        (size[0], -size[1], 0.0), # BR
        (0.0, 0.0, 0.0),  # TL
        (size[0], 0.0, 0.0)]  # TR

    uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
    faces = [(0, 1, 3, 2)]
    return points, faces, uvs

def create_rectangle_bmesh(size):
    bm = bmesh.new()
    verts, faces, uvs = rectangle_mesh_data(size)
    for v in verts:
        bm.verts.new(v)
    bm.verts.ensure_lookup_table()
    bm.faces.new( (bm.verts[i] for i in faces[0]) )
    bm.faces.ensure_lookup_table()

    # add uvs to the new face
    uv_layer = bm.loops.layers.uv.verify()
    face = bm.faces[-1]
    for i, loop in enumerate(face.loops):
        loop[uv_layer].uv = uvs[i]
    return bm

def screen_to_bl_size(screen_size):
    return [screen_size[0] / 120, screen_size[1] / 120, 1]

def vec3_approx_equals(vec, other, ep=.001):
    diff = [vec[0] - other[0], 
            vec[1] - other[1],
            vec[2] - other[2]]
    for d in diff:
        if abs(d) > ep: return False
    return True

def update_active_object(context):
    can_update = bpy.ops.object.mode_set.poll()
    if can_update:
        mode = context.mode
        bpy.ops.object.mode_set(mode="EDIT", toggle=False)
        bpy.ops.object.mode_set(mode="OBJECT", toggle=False)
        bpy.ops.object.mode_set(mode=mode, toggle=False)
    return can_update

def is_renderable(obj_state):
    return not vec3_approx_equals(obj_state.bounds.get_dimensions(), (0, 0, 0))

def room_script_exists(scene_name, room_name, variant_name):
    script_filepath = asset_abspath(room_script_assetpath(scene_name, room_name, variant_name))
    return os.path.exists(script_filepath)

def create_room_script(scene_name, room_name, variant_name):
    try:
        template_filepath = os.path.normpath(os.path.abspath(os.path.dirname(__file__) + "/ecs/templates/smithy_state_script_template.txt"))
        with open(template_filepath, "r") as template_file:
            script_template = template_file.read()

        output_filepath = asset_abspath(room_script_assetpath(scene_name, room_name, variant_name))
        os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
        print("Making State Script: ", output_filepath)

        with open(output_filepath, "w") as script_file:
            script_file.write(script_template)

        return output_filepath
    except:
        return None

# get filepath relative to the image folder
def get_image_dir():
    return "//gamedata/img/"

def get_asset_dir():
    return "//gamedata/"

def asset_abspath(assetpath):
    return "{}gamedata/assets/{}".format(bpy.path.abspath("//").replace('\\', '/'), assetpath)

def asset_archive_abspath(assetpath):
    return "{}.lexeditor/.tmp/gamedata/assets/{}".format(bpy.path.abspath("//").replace('\\', '/'), assetpath)

def global_component_assetpath(component_name):
    return "scripts/core/components/{}.lua".format(component_name)

def component_assetpath(component_name, scene_name, room_name):
    return "scripts/{}/{}/components/{}.lua".format(scene_name, room_name, component_name)

def get_component_from_asset(assetpath):
    asset_parts = assetpath.split("/")
    if asset_parts[1] == 'core':
        return 'core', None, os.path.splitext(asset_parts[-1])[0]
    else:
        return asset_parts[1], asset_parts[2], os.path.splitext(asset_parts[4])[0]

def component_idpath(assetpath):
    scene, room, component = get_component_from_asset(assetpath)
    if scene == 'core':
        return "{}/{}".format(scene, component)
    else:
        return "{}/{}/{}".format(scene, room, component)

def room_script_assetpath(scene_name, room_name, variant_name):
    return "scripts/{}/{}/states/{}.lua".format(scene_name, room_name, variant_name)

def asset_scriptpath(assetpath):
    return os.path.relpath(assetpath, start="scripts").replace('\\', '/')

def room_dir_assetpath(scene_name, room_name):
    return "scripts/{}/{}".format(scene_name, room_name)

def scene_dir_assetpath(scene_name):
    return "scripts/{}".format(scene_name)

def room_scriptpath(scene_name, room_name, variant_name):
    return asset_scriptpath(room_script_assetpath(scene_name, room_name, variant_name))

def valid_scene_assetpath(assetpath):
    asset_normpath = os.path.normpath(assetpath)
    path_parts = asset_normpath.split(os.sep)
    valid = (len(path_parts) == 2 
        and path_parts[0].lower() == "scripts" 
        and path_parts[1].lower() != "core")
    return valid

def valid_room_assetpath(assetpath):
    asset_normpath = os.path.normpath(assetpath)
    path_parts = asset_normpath.split(os.sep)
    valid = (len(path_parts) == 3 
        and path_parts[0].lower() == "scripts" 
        and path_parts[1].lower() != "core")
    return valid

def valid_variant_assetpath(assetpath):
    asset_normpath = os.path.normpath(assetpath)
    path_parts = asset_normpath.split(os.sep)
    valid = (len(path_parts) == 5 
        and path_parts[0].lower() == "scripts" 
        and path_parts[3].lower() == "states" 
        and path_parts[1].lower() != "core"
        and os.path.splitext(path_parts[4])[1] == ".lua")
    return valid

def get_guid_mapfile():
    return os.path.join(bpy.path.abspath("//"), ".lexeditor", "guids")

def scene_from_assetpath(assetpath):
    if valid_scene_assetpath(assetpath):
        asset_normpath = os.path.normpath(assetpath)
        path_parts = asset_normpath.split(os.sep)
        return path_parts[1]
    else:
        return None

def room_from_assetpath(assetpath):
    if valid_room_assetpath(assetpath):
        asset_normpath = os.path.normpath(assetpath)
        path_parts = asset_normpath.split(os.sep)
        return path_parts[2]
    else:
        return None

def variant_from_assetpath(assetpath):
    if valid_variant_assetpath(assetpath):
        asset_normpath = os.path.normpath(assetpath)
        path_parts = asset_normpath.split(os.sep)
        return os.path.splitext(path_parts[4])[0]
    else:
        return None

def get_unique_scene_name(scene_basename):
    final_name = scene_basename
    i = 0
    found_name = False
    while not found_name:
        scene_dir_abspath = asset_abspath(scene_dir_assetpath(final_name))
        if not os.path.exists(scene_dir_abspath):
            found_name = True
        else:  
            i += 1
            final_name = scene_basename + "_" + str(i)
    return final_name

def get_unique_room_name(scene_name, room_basename):
    final_name = room_basename
    i = 0
    found_name = False
    while not found_name:
        room_dir_abspath = asset_abspath(room_dir_assetpath(scene_name, final_name))
        if not os.path.exists(room_dir_abspath):
            found_name = True
        else:  
            i += 1
            final_name = room_basename + "_" + str(i)
    return final_name

def get_unique_variant_name(scene_name, room_name, variant_basename):
    final_name = variant_basename
    i = 0
    found_name = False
    while not found_name:
        variant_script_filepath = asset_abspath(room_script_assetpath(scene_name, room_name, final_name))
        if not os.path.exists(variant_script_filepath):
            found_name = True
        else:  
            i += 1
            final_name = variant_basename + "_" + str(i)
    return final_name