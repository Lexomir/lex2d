import bpy
import traceback
from .utils import *
from . import ecs
from mathutils import Vector

def obj_state_to_lua_string(obj_state, line_prefix):
    def convert_to_lua_value(datatype, val):
        if datatype == "string":
            return "\"" + val + "\""
        elif datatype == "vec2":
            return "{" + ",".join(map(str, val[0:2])) + "}" 
        elif datatype == "vec3":
            return "{" + ",".join(map(str, val[0:3])) + "}"
        elif datatype == "vec4":
            return "{" + ",".join(map(str, val[0:4])) + "}"
        elif val in ["", None]:
            return "nil"
        elif datatype == "float":
            return str(val)
        return "\"" + str(val) + "\""

    def convert_to_screen_position(blender_pos):
        return [(blender_pos[0] * 120), -(blender_pos[1] * 120), blender_pos[2]]

    def convert_to_screen_size(blender_size):
        return [blender_size[0] * 120, blender_size[1] * 120, blender_size[2]]

    serialized_state = "{}{{\n".format(line_prefix)
    serialized_state += "{}\tname = \"{}\",\n".format(line_prefix, obj_state.name)
    if obj_state.parent != "":
        serialized_state += "{}\tparent = \"{}\",\n".format(line_prefix, obj_state.parent)

    serialized_state += "{}\tcomponents = {{\n".format(line_prefix)
    
    # transform component
    serialized_state += "{}\t\t[\"{}\"] = {{\n".format(line_prefix, component_idpath(global_component_assetpath("Transform")))

    loc, rot, scale = obj_state.matrix_local.decompose()
    mesh_size =  obj_state.bounds.get_dimensions()
    pivotpos_from_topleft = Vector(obj_state.topleft) * -1
    pivotpos_from_topleft_normalized = [a / b if b != 0 else a for a,b in zip(pivotpos_from_topleft, mesh_size)]
    pivotpos_from_topleft_normalized[1] *= -1  # invert y because topleft coordinate system
    transform_inputs = [
        ('position', 'vec3', [round(v, 3) for v in convert_to_screen_position(loc)]), 
        ('pivot', 'vec3', [round(v, 3) for v in pivotpos_from_topleft_normalized]), 
        ('rotation_quat', 'vec4', [round(v, 3) for v in rot]), 
        ('size', 'vec4', [round(v, 3) for v in convert_to_screen_size(mesh_size)]), 
        ('scale', 'vec3', [round(v, 3) for v in scale])]
    for i_n, i_t, i_v in transform_inputs:
        serialized_state += "{}\t\t\t[\"{}\"]={},\n".format(line_prefix, i_n, convert_to_lua_value(i_t, i_v))

    serialized_state += "{}\t\t}},\n".format(line_prefix) # end component

    # other components
    for sc in obj_state.components_serialized:
        if sc.name:
            _, room, scene = obj_state.get_variant_room_scene()
            
            component = ecs.component_system.get_or_create_component(sc.get_assetpath(scene, room))
            ecs.component_system.recompile_component_if_changed(component)

            if component.file_exists():
                serialized_state += "{}\t\t[\"{}\"] = {{\n".format(line_prefix, component_idpath(sc.get_assetpath(scene, room)))

                stored_inputs = ecs.inputs_from_serialized_component(sc)
                inputs = ecs.override_script_inputs(base_inputs=component.inputs, overrides=stored_inputs)

                for i in inputs:
                    try:
                        input_name, input_datatype, input_value, input_args = i
                        serialized_state += "{}\t\t\t[\"{}\"]={},\n".format(line_prefix, input_name, convert_to_lua_value(input_datatype, input_value))
                    except:
                        print("ERROR: Invalid component input in a state for object '{}', component '{}', input ['{}']".format(
                            obj_state.name, sc.get_assetpath(scene, room), i[0]))
                        raise
                serialized_state += "{}\t\t}},\n".format(line_prefix) # end component 

    serialized_state += line_prefix + "\t}\n" # end component list
    serialized_state += line_prefix + "}" # end object state
    return serialized_state

def scene_to_lua_string(scene):
    print("Exporting scene '{}'".format(scene.name))

    serialized_scene = "\t[\"{}\"] = {{\n".format(scene.name)   # export scene
    for room in scene.rooms:
        serialized_scene += "\t\t[\"{}\"] = {{\n".format(room.name)   # export room
        for variant in room.variants:
            # create state script if it doesnt exist
            try:
                if not variant_script_exists(scene.name, room.name, variant.name):
                    create_variant_script(scene.name, room.name, variant.name)
            except Exception as err:
                print(err)
                raise
            
            # export state node
            serialized_scene += "\t\t\t[\"{}\"] = {{\n".format(variant.name)
            serialized_scene += "\t\t\t\t{} = \"{}\",\n".format("script", variant_scriptpath(scene.name, room.name, variant.name))
            
            serialized_scene += "\t\t\t\tobjects = {\n"  # object list

            obj_states = variant.object_states
            for obj_state in obj_states:
                serialized_scene += obj_state_to_lua_string(obj_state, "\t\t\t\t\t") + ",\n"
            
            serialized_scene += "\t\t\t\t}\n\t\t\t},\n"  # end object list + end variant
        serialized_scene += "\t\t},\n" # end room

    serialized_scene += "\t},\n" # end scene
    return serialized_scene

def export_scene_definition(scene):
    serialized_scene = "return {\n"
    serialized_scene += scene_to_lua_string(scene)
    serialized_scene += "}\n"

    abs_output_dir = asset_abspath(scene_dir_assetpath(scene.name))
    os.makedirs(abs_output_dir, exist_ok=True)
    output_filepath = os.path.join(abs_output_dir, ".definition.lua")
    with open(output_filepath, 'w') as f:
        f.write(serialized_scene)
        
def export_scene_states():
    # export the scene states into separate files
    for scene in bpy.context.scene.smithy2d.scenes:
        export_scene_definition(scene)

# get all global component assetpaths
def get_valid_global_component_assetpaths(bpy_scene):
    component_assetpaths = set()
    for scene in bpy_scene.smithy2d.scenes:
        for room in scene.rooms:
            for variant in room.variants:
                for obj_state in variant.object_states:
                    for sc in obj_state.components_serialized:
                        if sc.is_global:
                            assetpath = global_component_assetpath(sc.name)
                            component_assetpaths.add(assetpath)

    return [path for path in component_assetpaths if os.path.exists(asset_abspath(path))]

# get all non-global component assetpaths for a scene
def get_valid_component_assetpaths_for_scene(scene):
    component_assetpaths = set()
    for room in scene.rooms:
        for variant in room.variants:
            for obj_state in variant.object_states:
                for sc in obj_state.components_serialized:
                    if not sc.is_global:
                        assetpath = component_assetpath(sc.name, scene.name, room.name)
                        component_assetpaths.add(assetpath)

    return [path for path in component_assetpaths if os.path.exists(asset_abspath(path))]

def export_component_includes_file(output_filepath, component_assetpaths):
    with open(bpy.path.abspath(output_filepath), 'w') as f:
        f.write("return {\n")
        for asset in component_assetpaths:
            f.write('\t{{"{}", "{}"}},\n'.format(component_idpath(asset), asset_scriptpath(asset)))
        f.write("}")

class Smithy2D_ExportSceneStates(bpy.types.Operator):
    bl_idname = "smithy2d.export_scene_states"
    bl_label = "Smithy2D Export Scene States"

    def execute(self, context):
        # save the current state
        scene = context.scene.smithy2d.get_active_scene()
        scene.dirty = True # always export the active scene
        room = scene.get_active_room()
        if room:
            variant = room.get_active_variant()
            if variant: 
                variant.save_scene_state(context.scene)

        # try exporting all scenes     
        try:
            # export global component includes file
            global_component_includes_filepath = "{}scripts/core/.component_includes.lua".format(get_asset_dir())
            component_assetpaths = get_valid_global_component_assetpaths(context.scene)
            export_component_includes_file(global_component_includes_filepath, component_assetpaths)
            
            for scene in context.scene.smithy2d.scenes:
                if scene.dirty:
                    scene.dirty = False
                    # export scene component includes file
                    component_includes_filepath = "{}/.component_includes.lua".format(asset_abspath(scene_dir_assetpath(scene.name)))
                    component_assetpaths = get_valid_component_assetpaths_for_scene(scene)
                    export_component_includes_file(component_includes_filepath, component_assetpaths)

                    # export scene definition
                    export_scene_definition(scene)

        except Exception as err:
            traceback.print_tb(err.__traceback__)
            print(err)
            self.report({"ERROR"}, "Error encountered while exporting scene states. See Console.")
        return {'FINISHED'}
