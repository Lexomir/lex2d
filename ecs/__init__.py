import bpy
import os

# external interface for smithy2d.ecs

def get_component_system():
    from . import component_system
    return component_system

_component_update_callbacks = []

def on_component_updated(scene, obj, component_instance):
    for cb in _component_update_callbacks:
        cb(scene, obj, component_instance)

def add_component_updated_callback(func):
    _component_update_callbacks.append(func)

def remove_component_updated_callback(func):
    _component_update_callbacks.remove(func)

# -----------------------------------------------------------------------

def validate_input(name, datatype, value, args):
    try:
        if datatype == "": return False
        elif datatype == 'enum' and value not in args: return False
        elif datatype in ['float', 'int']: return float(args[0]) <= float(value) <= float(args[1])
        elif 'vec' in datatype: return len(value) > 0 and isinstance(value[0], (int, float))
        elif datatype == 'string': return type(value).__name__ == 'str' and value
        else:
            return True
    except:
        return False

def deserialize_value(datatype, string_val):
    def deserialize_vec(vec_string):
        return [float(str_val) for str_val in vec_string.split(',')]

    if datatype == 'int': return int(float(string_val))
    elif datatype == 'float': return float(string_val)
    elif datatype == 'bool': return bool(string_val != "False" and string_val)
    elif datatype == 'vec2': return deserialize_vec(string_val)
    elif datatype == 'vec3': return deserialize_vec(string_val)
    elif datatype == 'vec4': return deserialize_vec(string_val)
    else: return string_val or ""

def inputs_from_bpy_component(bpy_component):
    inputs = []
    for bpy_input in bpy_component.inputs:
        val = deserialize_value(bpy_input.datatype, bpy_input.get_string())
        inputs.append((bpy_input.name, bpy_input.datatype, val, bpy_input.get_args()))
    return inputs

def inputs_from_serialized_component(serialized_component):
    serialized_inputs = serialized_component.data
    if not serialized_inputs:
        return []

    input_strs = serialized_inputs.split('\n')
    
    inputs = []
    for input_str in input_strs:
        name, datatype, str_value = input_str.split(",", 2)
        value = deserialize_value(datatype, str_value)
        inputs.append((name, datatype, value, []))

    return inputs

def override_script_inputs(base_inputs, overrides):
    def find_input_by_name(name, inputs):
        for i in inputs:
            i_name, i_datatype, i_default_val, i_args = i
            if i_name == name: return i
        return None

    inputs = []
    for base_input in base_inputs:
        name, datatype, default_value, args = base_input

        override_input = find_input_by_name(name, overrides)

        success = False
        if override_input:
            ov_name, ov_datatype, ov_value, ov_args = override_input
            valid = validate_input(name, datatype, ov_value, args)
            if valid:
                inputs.append((name, datatype, ov_value, args))
                success = True

        if not success:
            inputs.append((name, datatype, default_value, args))

    return inputs
