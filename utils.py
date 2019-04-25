import bpy
import sys
import os
import bmesh


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

def set_material_image_texture(obj, image_filepath, tile_size=None):
    # import image file
    image = bpy.data.images.load(bpy.path.relpath(image_filepath), check_existing=True)

    material = bpy.data.materials.get(obj.name)
    if not material:
        material = bpy.data.materials.new(obj.name)
    material.use_nodes = True

    mat_output = get_active_material_output(material.node_tree.nodes)
    texture_node = get_or_create_input_node(material.node_tree, mat_output, "ShaderNodeTexImage", "Color", "Surface")
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

# get filepath relative to the image folder
def get_image_dir():
    return "//gamedata/img/"

def get_asset_dir():
    return "//gamedata/"

