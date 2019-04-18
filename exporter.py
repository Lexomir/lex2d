import bpy
from .utils import *

def serialize_obj_state(obj_state, line_prefix):
    def convert_to_lua_value(datatype, string_val):
        if datatype == "string":
            return "\"" + string_val + "\""
        elif datatype == "vec2":
            return "{" + ",".join(string_val.split(",")[0:2]) + "}" 
        elif datatype == "vec3":
            return "{" + ",".join(string_val.split(",")[0:3]) + "}"
        elif datatype == "vec4":
            return "{" + string_val + "}"
        elif string_val in ["", None]:
            return "nil"
        return string_val

    def convert_to_screen_position(blender_pos):
        return [(blender_pos[0] * 120), -(blender_pos[1] * 120), blender_pos[2]]

    def convert_to_screen_size(blender_size):
        return [blender_size[0] * 120, blender_size[1] * 120, blender_size[2]]

    serialized_state = "{}{{\n".format(line_prefix)
    serialized_state += "{}\tname = \"{}\",\n".format(line_prefix, obj_state.name)

    serialized_state += "{}\tcomponents = {{\n".format(line_prefix)
    
    # transform component
    serialized_state += "{}\t\t[\"Transform\"] = {{\n".format(line_prefix)

    transform_inputs = [
        ('position', 'vec3', ",".join([str(round(v, 3)) for v in convert_to_screen_position(obj_state.location)])), 
        ('rotation_quat', 'vec4', ",".join([str(round(v, 3)) for v in obj_state.rotation_quaternion])), 
        ('size', 'vec3', ",".join([str(round(v, 3)) for v in convert_to_screen_size(obj_state.scale)]))]
    for i_n, i_t, i_v in transform_inputs:
        serialized_state += "{}\t\t\t[\"{}\"]={},\n".format(line_prefix, i_n, convert_to_lua_value(i_t, i_v))

    serialized_state += "{}\t\t}},\n".format(line_prefix) # end component

    # other components
    for sc in obj_state.smithy_components_serialized:
        if sc.filepath:
            serialized_state += "{}\t\t[\"{}\"] = {{\n".format(line_prefix, sc.filepath)

            sinputs = sc.data.split("\n")
            for si in sinputs:
                try:
                    input_name, input_datatype, input_str_value = si.split(",", 2)
                    serialized_state += "{}\t\t\t[\"{}\"]={},\n".format(line_prefix, input_name, convert_to_lua_value(input_datatype, input_str_value))
                except:
                    print("ERROR: Invalid component input in a state for object '{}', component '{}', input ['{}']".format(obj_state.name, sc.filepath, si))
                    raise

        serialized_state += "{}\t\t}},\n".format(line_prefix) # end component 

    serialized_state += line_prefix + "\t}\n" # end component list
    serialized_state += line_prefix + "}" # end object state
    return serialized_state


def export_scene_states(scene, output_filepath):
    nodegroup = scene.lexsm.get_nodegroup()
    if nodegroup:
        nodegroup.save_current_state()
        with open(bpy.path.abspath(output_filepath), 'w') as f:
            serialized_scene = "return {\n"
            for node in nodegroup.nodes:
                #serialize_state += node.serialized_hierarchy
                
                serialized_scene += "\t[\"{}\"] = {{\n".format(node.name)
                serialized_scene += "\t\tobjects = {\n"

                obj_states = node.object_states
                for obj_state in obj_states:
                    serialized_scene += serialize_obj_state(obj_state, "\t\t\t") + ",\n"
                
                serialized_scene += "\t\t}\n\t},\n"  # end object list

            serialized_scene += "}\n" # end scene list
            f.write(serialized_scene)
                

class export_scene_states_operator(bpy.types.Operator):
    bl_idname = "lex2d.export_scene_states"
    bl_label = "Lex2D Export Scene States"

    def execute(self, context):
        blend_name = bpy.path.display_name(bpy.data.filepath)
        output_filepath = "{}/{}.lua".format(get_asset_dir(), blend_name)
        try:
            for scene in bpy.data.scenes:
                scene.lexsm.get_nodegroup().save_current_state()
            export_scene_states(context.scene, output_filepath)
        except:
            self.report({"ERROR"}, "Error encountered while exporting scene states. See Console.")
        return {'FINISHED'}
