import bpy
from .utils import *
from . import ecs

def serialize_obj_state(obj_state, line_prefix):
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
    serialized_state += "{}\tcomponents = {{\n".format(line_prefix)
    
    # transform component
    serialized_state += "{}\t\t[\"{}\"] = {{\n".format(line_prefix, component_idpath(global_component_assetpath("Transform")))

    obj_size = obj_state.dimensions if is_renderable(obj_state) else obj_state.scale
    transform_inputs = [
        ('position', 'vec3', [round(v, 3) for v in convert_to_screen_position(obj_state.location)]), 
        ('rotation_quat', 'vec4', [round(v, 3) for v in obj_state.rotation_quaternion]), 
        ('size', 'vec3', [round(v, 3) for v in convert_to_screen_size(obj_size)])]
    for i_n, i_t, i_v in transform_inputs:
        serialized_state += "{}\t\t\t[\"{}\"]={},\n".format(line_prefix, i_n, convert_to_lua_value(i_t, i_v))

    serialized_state += "{}\t\t}},\n".format(line_prefix) # end component

    # other components
    for sc in obj_state.components_serialized:
        if sc.name:
            scene = obj_state.get_variant().get_room().get_scene()
            serialized_state += "{}\t\t[\"{}\"] = {{\n".format(line_prefix, component_idpath(sc.get_assetpath(scene, obj_state.get_variant().get_room())))
            
            component = ecs.component_system.get_or_create_component(sc.get_assetpath(scene, obj_state.get_variant().get_room()))
            ecs.component_system.recompile_component_if_changed(component)

            stored_inputs = ecs.inputs_from_serialized_component(sc)
            inputs = ecs.override_script_inputs(base_inputs=component.inputs, overrides=stored_inputs)

            for i in inputs:
                try:
                    input_name, input_datatype, input_value, input_args = i
                    serialized_state += "{}\t\t\t[\"{}\"]={},\n".format(line_prefix, input_name, convert_to_lua_value(input_datatype, input_value))
                except:
                    print("ERROR: Invalid component input in a state for object '{}', component '{}', input ['{}']".format(
                        obj_state.name, sc.get_assetpath(scene, obj_state.get_room()), i[0]))
                    raise
        serialized_state += "{}\t\t}},\n".format(line_prefix) # end component 

    serialized_state += line_prefix + "\t}\n" # end component list
    serialized_state += line_prefix + "}" # end object state
    return serialized_state


def export_scene_states(output_filepath):

    with open(bpy.path.abspath(output_filepath), 'w') as f:
        serialized_scene = "return {\n"

        for scene in bpy.context.scene.smithy2d.scenes:
            print("Exporting scene '{}'".format(scene.name))

            serialized_scene += "\t[\"{}\"] = {{\n".format(scene.name)   # export dungeon
            for room in scene.rooms:
                serialized_scene += "\t\t[\"{}\"] = {{\n".format(room.name)   # export room
                for variant in room.variants:
                    # create state script if it doesnt exist
                    try:
                        if not room_script_exists(scene.name, room.name, variant.name):
                            create_room_script(scene.name, room.name, variant.name)
                    except Exception as err:
                        print(err)
                        raise
                    
                    # export state node
                    serialized_scene += "\t\t\t[\"{}\"] = {{\n".format(variant.name)
                    serialized_scene += "\t\t\t\t{} = Engine.require(\"{}\"),\n".format("script", room_scriptpath(scene.name, room.name, variant.name))
                    
                    serialized_scene += "\t\t\t\tobjects = {\n"  # object list

                    obj_states = variant.object_states
                    for obj_state in obj_states:
                        serialized_scene += serialize_obj_state(obj_state, "\t\t\t\t\t") + ",\n"
                    
                    serialized_scene += "\t\t\t\t}\n\t\t\t},\n"  # end object list + end variant
                serialized_scene += "\t\t},\n" # end room

            serialized_scene += "\t},\n" # end dungeon
        serialized_scene += "}\n" # end dungeon list
        f.write(serialized_scene)


def export_component_include_file(output_filepath):
    with open(bpy.path.abspath(output_filepath), 'w') as f:
        components = ecs.get_component_system().get_all_component_assetpaths()
        for c in components:
            f.write('Component["{}"] = Engine.require("{}")\n'.format(component_idpath(c), asset_scriptpath(c)))

class export_scene_states_operator(bpy.types.Operator):
    bl_idname = "smithy2d.export_scene_states"
    bl_label = "Smithy2D Export Scene States"

    def execute(self, context):
        scene_states_filepath = "{}/assets/scripts/scene_states.lua".format(get_asset_dir())
        component_includes_filepath = "{}/assets/scripts/blend_includes.lua".format(get_asset_dir())

        # save the current state
        room = context.scene.smithy2d.get_active_scene().get_active_room()
        if room:
            variant = room.get_active_variant()
            if variant: 
                variant.save_scene_state(context.scene)

        # try exporting all scenes     
        try:
            export_scene_states(scene_states_filepath)
            export_component_include_file(component_includes_filepath)
        except Exception as err:
            print(err)
            self.report({"ERROR"}, "Error encountered while exporting scene states. See Console.")
        return {'FINISHED'}
