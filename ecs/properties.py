import bpy
from ..utils import *
from ..generic_value import GenericValue 



class Smithy2D_ComponentInput(bpy.types.PropertyGroup, GenericValue):
    def on_value_updated(self, prev_value, curr_value):
        from . import component_system
        obj = self.id_data
        smithy_component = obj.path_resolve(".".join(self.path_from_id().split('.')[0:-1]))
        component_system.input_updated(smithy_component, self)

class Smithy2D_Component(bpy.types.PropertyGroup):
    def get_name(self):
        return os.path.splitext(os.path.basename(self.filepath))[0]

    def set_filepath_and_update(self, filepath):
        from . import component_system
        if filepath != self.filepath:
            self['filepath'] = filepath
            component_system.refresh_inputs(self)
            # TODO compute inputs

    def set_filepath(self, filepath):
        self['filepath'] = filepath

    def get_filepath(self):
        return self['filepath'] if 'filepath' in self else ""            

    def valid(self):
        return self.err_log == "" and self.filepath != ""

    def get_input(self, name):
        i = self.inputs.get(name)
        return i.get_value() if i else None
    
    def set_input(self, name, value):
        i = self.inputs.get(name)
        if i:
            i.set_value(value)

    def refresh(self):
        pass

    filepath : bpy.props.StringProperty(default="", set=set_filepath_and_update, get=get_filepath)
    inputs : bpy.props.CollectionProperty(type=Smithy2D_ComponentInput)
    file_exists : bpy.props.BoolProperty(default=False)
    err_log : bpy.props.StringProperty(default="")

