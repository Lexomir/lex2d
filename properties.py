import bpy
from . import statemachine
from . import ecs
from .utils import *


class Smithy2D_Object(bpy.types.PropertyGroup):
    def get_component(self, name):
        for c in self.components:
            if c.name == name:
                return c
    
    def add_component(self, name, is_global=False):
        c = self.get_component(name)
        if not c:
            c = self.components.add()
            c.set_name(name)
            c.set_is_global(is_global)
            self.get_component_system().refresh_inputs(c)
        return c

    def remove_component(self, name):
        for i, c in enumerate(reversed(self.components)):
            if c.name == name:
                self.components.remove(i)

    def get_components(self):
        return self.components[:]

    def get_component_system(self):
        return ecs.component_system
    
    active_component_index : bpy.props.IntProperty(default=-1)
    components : bpy.props.CollectionProperty(type=ecs.properties.Smithy2D_Component)

class Smithy2D_Image(bpy.types.PropertyGroup):
    is_map : bpy.props.BoolProperty(default=False)

class Smithy2D_Scene(bpy.types.PropertyGroup):
    def set_room_and_update(self, index):
        scene = self.id_data
        old_index = self.active_room_index
        old_room = self.rooms[old_index] if old_index >= 0 else None
        old_variant = old_room.get_active_variant() if old_room else None
        room = self.rooms[index] if index >= 0 else None
        variant = room.get_active_variant() if room else None
        switch_state((scene, old_room, old_variant), (scene, room, variant))
        
        self['active_room_index'] = index

    def set_room(self, index):
        self['active_room_index'] = index

    def get_room(self):
        return self.get('active_room_index', -1)

    def get_active_room(self):
        if self.active_room_index >= 0 and self.rooms:
            return self.rooms[self.active_room_index]
        return None

    def get_statemachine(self):
        return statemachine.get_statemachine(self.get_statemachine_name())

    def get_statemachine_name(self):
        # for some reason blender puts three spaces in the beginning (if you select it with prop_search)
        if self.statemachine_name[:3] == '   ':
            return self.statemachine_name[3:]
        else:
            return self.statemachine_name

    statemachine_name : bpy.props.StringProperty()
    rooms : bpy.props.CollectionProperty(type=ecs.properties.Smithy2D_Room)
    active_room_index : bpy.props.IntProperty(default=-1, get=get_room, set=set_room_and_update)

def register():
    bpy.types.Object.smithy2d = bpy.props.PointerProperty(type=Smithy2D_Object)
    bpy.types.Scene.smithy2d = bpy.props.PointerProperty(type=Smithy2D_Scene)
    bpy.types.Image.smithy2d = bpy.props.PointerProperty(type=Smithy2D_Image)

def unregister():
    del bpy.types.Object.smithy2d
    del bpy.types.Scene.smithy2d
    del bpy.types.Image.smithy2d
