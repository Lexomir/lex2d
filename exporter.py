import bpy
from .utils import *

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
        return str(val)

    def convert_to_screen_position(blender_pos):
        return [(blender_pos[0] * 120), -(blender_pos[1] * 120), blender_pos[2]]

    def convert_to_screen_size(blender_size):
        return [blender_size[0] * 120, blender_size[1] * 120, blender_size[2]]

    serialized_state = "{}{{\n".format(line_prefix)
    serialized_state += "{}\tname = \"{}\",\n".format(line_prefix, obj_state.name)
    serialized_state += "{}\tcomponents = {{\n".format(line_prefix)
    
    # transform component
    serialized_state += "{}\t\t[\"Transform\"] = {{\n".format(line_prefix)

    obj_size = obj_state.dimensions if is_renderable(obj_state) else obj_state.scale
    transform_inputs = [
        ('position', 'vec3', [round(v, 3) for v in convert_to_screen_position(obj_state.location)]), 
        ('rotation_quat', 'vec4', [round(v, 3) for v in obj_state.rotation_quaternion]), 
        ('size', 'vec3', [round(v, 3) for v in convert_to_screen_size(obj_size)])]
    for i_n, i_t, i_v in transform_inputs:
        serialized_state += "{}\t\t\t[\"{}\"]={},\n".format(line_prefix, i_n, convert_to_lua_value(i_t, i_v))

    serialized_state += "{}\t\t}},\n".format(line_prefix) # end component

    # other components
    for sc in obj_state.smithy_components_serialized:
        if sc.filepath:
            serialized_state += "{}\t\t[\"{}\"] = {{\n".format(line_prefix, sc.filepath)
            
            from . import get_lex_suite
            lex_game = get_lex_suite().lex_game
            component = lex_game.smithy.get_component_system().get_or_create_component(sc.filepath)
            lex_game.smithy.get_component_system().recompile_component_if_changed(component)

            stored_inputs = lex_game.inputs_from_serialized_component(sc)
            inputs = lex_game.override_script_inputs(base_inputs=component.inputs, overrides=stored_inputs)

            for i in inputs:
                try:
                    input_name, input_datatype, input_value, input_args = i
                    serialized_state += "{}\t\t\t[\"{}\"]={},\n".format(line_prefix, input_name, convert_to_lua_value(input_datatype, input_value))
                except:
                    print("ERROR: Invalid component input in a state for object '{}', component '{}', input ['{}']".format(obj_state.name, sc.filepath, i[0]))
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
                
                # create state script if it doesnt exist
                try:
                    from . import get_lex_suite
                    lex_smithy = get_lex_suite().lex_game.smithy
                    if not lex_smithy.state_script_exists(node.name):
                        lex_smithy.create_state_script(node.name)
                except Exception as err:
                    print(err)
                    raise
                    
                # export state node
                serialized_scene += "\t[\"{}\"] = {{\n".format(node.name)

                serialized_scene += "\t\t{} = {{\n".format("next_states")
                for node_output in node.outputs:
                    if node_output.links:
                        connected_state = node_output.links[0].to_node
                        serialized_scene += "\t\t\t\"{}\",\n".format(connected_state.name)
                serialized_scene += "\t\t}},\n".format("next_states")
                
                serialized_scene += "\t\tobjects = {\n"  # object list

                obj_states = node.object_states
                for obj_state in obj_states:
                    serialized_scene += serialize_obj_state(obj_state, "\t\t\t") + ",\n"
                
                serialized_scene += "\t\t}\n\t},\n"  # end object list

            serialized_scene += "}\n" # end state list
            f.write(serialized_scene)
                

class export_scene_states_operator(bpy.types.Operator):
    bl_idname = "lex2d.export_scene_states"
    bl_label = "Lex2D Export Scene States"

    def execute(self, context):
        blend_name = bpy.path.display_name(bpy.data.filepath)
        output_filepath = "{}/{}.lua".format(get_asset_dir(), blend_name)
        try:
            export_scene_states(context.scene, output_filepath)
        except Exception as err:
            print(err)
            self.report({"ERROR"}, "Error encountered while exporting scene states. See Console.")
        return {'FINISHED'}
