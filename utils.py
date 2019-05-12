import bpy
import sys
import shutil
import os
import bmesh

def refresh_screen_area(area_type):
    for area in bpy.context.screen.areas:
        if area.type == area_type:
            area.tag_redraw()


#recursively merge two folders including subfolders
def merge_overwrite(root_src_dir, root_dst_dir):
    for src_dir, dirs, files in os.walk(root_src_dir):
        dst_dir = src_dir.replace(root_src_dir, root_dst_dir, 1)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        for file_ in files:
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

def switch_state(old_state, new_state):
    old_scene, old_room, old_variant = old_state
    scene, room, variant = new_state
    def name(item):
        return item.name if item else "_"
    print("Switching from {}:{}:{} to {}:{}:{}".format(
        name(old_scene), name(old_room), name(old_variant), 
        name(scene), name(room), name(variant)))
    if old_variant:
        old_variant.save_scene_state(old_scene)
    
    if room:
        scene.smithy2d.set_room(room.index())
        if variant:
            room.set_variant(variant.index())
            variant.load_scene_state(scene)

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
    active_obj = bpy.context.view_layer.objects.active
    bpy.context.view_layer.objects.active = obj
    mode = bpy.context.mode
    bpy.ops.object.mode_set(mode='OBJECT')
    bm.to_mesh(obj.data)
    bpy.ops.object.mode_set(mode=mode)
    bpy.context.view_layer.objects.active = active_obj

def get_or_create_input_node(node_tree, src_node, input_node_type, from_output_name, to_input_name):
    connected_node = None
    src_input = src_node.inputs[to_input_name]
    if src_input.links:
        connected_node = src_input.links[0].from_node
    if connected_node and type(connected_node).__name__ != input_node_type:
        connected_node = None
        node_tree.links.remove(src_input.links[0])

    if not connected_node:
        connected_node = node_tree.nodes.new(input_node_type)
        node_tree.links.new(src_input, connected_node.outputs[from_output_name])
    
    return connected_node

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
    if mat_output.inputs['Surface'].links and type(mat_output.inputs['Surface'].links[0].from_node).__name__ != "ShaderNodeEmission":
        remove_all_except(material.node_tree.nodes, [mat_output])

    emission_node = get_or_create_input_node(material.node_tree, mat_output, "ShaderNodeEmission", "Emission", "Surface")
    texture_node = get_or_create_input_node(material.node_tree, emission_node, "ShaderNodeTexImage", "Color", "Color")
    texture_node.image = image

    # connect a mapping node (to only display one tile of the texture)
    tile_size = tile_size or image.size
    mapping_node = get_or_create_input_node(material.node_tree, texture_node, "ShaderNodeMapping", "Vector", "Vector")
    tex_coord_node = get_or_create_input_node(material.node_tree, mapping_node, "ShaderNodeTexCoord", "UV", "Vector")

    mapping_node.vector_type = "TEXTURE"
    tile_count_x = round(image.size[0] / tile_size[0], 3)
    tile_count_y = round(image.size[1] / tile_size[1], 3)

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

def is_renderable(obj_state):
    return not vec3_approx_equals(obj_state.dimensions, (0, 0, 0))

def room_script_exists(scene_name, room_name, variant_name):
    script_filepath = asset_abspath(room_script_assetpath(scene_name, room_name, variant_name))
    return os.path.exists(script_filepath)

def create_room_script(scene_name, room_name, variant_name):
    template_filepath = os.path.normpath(os.path.abspath(os.path.dirname(__file__) + "/ecs/templates/smithy_state_script_template.txt"))
    with open(template_filepath, "r") as template_file:
        script_template = template_file.read()

    output_filepath = asset_abspath(room_script_assetpath(scene_name, room_name, variant_name))
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    print("Making State Script: ", output_filepath)

    with open(output_filepath, "w") as script_file:
        script_file.write(script_template)

    return output_filepath

# get filepath relative to the image folder
def get_image_dir():
    return "//gamedata/img/"

def get_asset_dir():
    return "//gamedata/"

def asset_abspath(assetpath):
    return bpy.path.abspath("//") + "gamedata/assets/{}".format(assetpath)

def global_component_assetpath(component_name):
    return "scripts/core/components/{}.lua".format(component_name)

def component_assetpath(component_name, scene_name, room_name):
    return "scripts/{}/{}/components/{}.lua".format(scene_name, room_name, component_name)

def room_script_assetpath(scene_name, room_name, variant_name):
    return "scripts/{}/{}/states/{}.lua".format(scene_name, room_name, variant_name)

def asset_scriptpath(assetpath):
    return os.path.relpath(assetpath, start="scripts") 

def room_dir_assetpath(room_name):
    return "scripts/{}".format(room_name)

def room_scriptpath(scene_name, room_name, variant_name):
    return asset_scriptpath(room_script_assetpath(scene_name, room_name, variant_name))