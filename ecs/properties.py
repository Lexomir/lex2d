import bpy
import sys
import shutil
from ..utils import *
from ..generic_value import GenericValue 
from .. import ObjUtils
from mathutils import Vector


class Smithy2D_ComponentInput(bpy.types.PropertyGroup, GenericValue):
    def on_value_updated(self, prev_value, curr_value):
        from . import component_system
        obj = self.id_data
        smithy_component = obj.path_resolve(".".join(self.path_from_id().split('.')[0:-1]))
        component_system.input_updated(smithy_component, self)

class Smithy2D_Component(bpy.types.PropertyGroup):
    def set_name_and_update(self, name):
        from . import component_system
        self['name'] = name
        scene = bpy.context.scene.smithy2d.get_active_scene()
        component_system.refresh_inputs(scene, scene.get_active_room(), self)
            # TODO compute inputs

    def get_assetpath(self, scene, room):
        if not self.name:
            return None
        elif self.is_global:
            return global_component_assetpath(self.name) if self.name else None
        else:
            return component_assetpath(self.name, scene.name, room.name) if room and scene else None

    def set_name(self, name):
        self['name'] = name

    def get_name(self):
        return self['name'] if 'name' in self else ""            

    def valid(self):
        return self.err_log == "" and self.name != ""

    def get_input(self, name):
        i = self.inputs.get(name)
        return i.get_value() if i else None
    
    def set_input(self, name, value, propagate=True):
        i = self.inputs.get(name)
        if i:
            i.set_value(value, propagate=propagate)

    def refresh(self):
        pass

    def set_is_global(self, is_global):
        self['is_global'] = is_global
    
    def set_is_global_and_update(self, is_global):
        self['is_global'] = is_global
        from . import component_system
        scene = bpy.context.scene.smithy2d.get_active_scene()
        component_system.refresh_inputs(scene, scene.get_active_room(), self)

    def get_is_global(self):
        return self.get('is_global', False)

    name : bpy.props.StringProperty(default="", set=set_name_and_update, get=get_name)
    is_global : bpy.props.BoolProperty(default=False, set=set_is_global_and_update, get=get_is_global)
    inputs : bpy.props.CollectionProperty(type=Smithy2D_ComponentInput)
    file_exists : bpy.props.BoolProperty(default=False)
    err_log : bpy.props.StringProperty(default="")

