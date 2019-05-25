import bpy
from . import ecs
from .utils import *
import time
import sys
from bpy.app.handlers import persistent


class Smithy2D_Object(bpy.types.PropertyGroup):
    def get_component(self, name):
        for c in self.components:
            if c.name == name:
                return c
    
    def add_component(self, name, is_global=False, calc_inputs=True):
        c = self.get_component(name)
        if not c:
            c = self.components.add()
            c.set_name(name)
            c.set_is_global(is_global)
            if calc_inputs:
                scene = bpy.context.scene.smithy2d.get_active_scene()
                self.get_component_system().refresh_inputs(scene, scene.get_active_room(), c)
        return c

    def remove_component(self, name):
        for i, c in reversed(list(enumerate(self.components))):
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


def _rename_smithy2d_scene(old_name, new_name):
    print("Renaming Scene '{}' to '{}'".format(old_name, new_name))
    old_scene_dir = scene_dir_assetpath(old_name)
    new_scene_dir = scene_dir_assetpath(new_name)
    move_merge_folders(asset_abspath(old_scene_dir), asset_abspath(new_scene_dir))

SMITHY2D_INVALID_ID = 0
class Smithy2D_Scene(bpy.types.PropertyGroup):
    def init(self, name):
        self.set_name(name)
        room = self.rooms.add().init("Room")
        self.set_room(0)

        return self

    def get_unique_name(self, name):
        bpy_scene = self.id_data
        final_name = name
        i = 0
        while bpy_scene.smithy2d.scenes.get(final_name) and final_name != self.name:
            i += 1
            final_name = name + "_" + str(i)
        
        return final_name

    def set_name(self, name):
        name = self.get_unique_name(name)
        self['name'] = name

    def set_name_and_update(self, name):
        name = self.get_unique_name(name)
        if name != self.get_name():
            _rename_smithy2d_scene(self.name, name)
            self['name'] = name
        
    def get_name(self):
        return self['name'] if 'name' in self else ''

    def set_room_and_update(self, index):
        old_index = self.active_room_index
        old_room = self.rooms[old_index] if old_index >= 0 else None
        old_variant = old_room.get_active_variant() if old_room else None
        room = self.rooms[index] if index >= 0 else None
        variant = room.get_active_variant() if room else None
        switch_state((self, old_room, old_variant), (self, room, variant))
        
        self['active_room_index'] = index

    def set_room(self, index):
        self['active_room_index'] = index

    def get_id(self):
        if "id" not in self.keys():
            return SMITHY2D_INVALID_ID
        return self["id"]

    def get_index(self):
        bpy_scene = self.id_data
        for i, s in enumerate(bpy_scene.smithy2d.scenes):
            if s == self:
                return i
        return None

    def get_room(self):
        return self.get('active_room_index', -1)

    def get_active_room(self):
        if self.active_room_index >= 0 and self.rooms:
            return self.rooms[self.active_room_index]
        return None

    def get_map_image(self):
        return bpy.data.images.get(self.map_image)

    name : bpy.props.StringProperty(set=set_name_and_update, get=get_name)
    rooms : bpy.props.CollectionProperty(type=ecs.properties.Smithy2D_Room)
    active_room_index : bpy.props.IntProperty(default=-1, get=get_room, set=set_room_and_update)
    map_image : bpy.props.StringProperty()


def _scene_changed(old_scene, new_scene):
        old_room = old_scene.get_active_room() if old_scene else None
        old_variant = old_room.get_active_variant() if old_room else None
        new_room = new_scene.get_active_room() if new_scene else None
        new_variant = new_room.get_active_variant() if new_room else None
        switch_state((old_scene, old_room, old_variant), (new_scene, new_room, new_variant))

class Smithy2D_ScenePropertyGroup(bpy.types.PropertyGroup):
    def get_active_scene(self):
        if self.scenes:
            return self.scenes[self.active_scene_index] if self.active_scene_index >= 0 else self.scenes[0]
        else:
            return None

    def set_scene(self, index):
        self['active_scene_index'] = index

    def set_scene_and_update(self, index):
        old_scene = self.get_active_scene() 
        new_scene = self.scenes[index] if self.scenes and index >= 0 else None
        _scene_changed(old_scene, new_scene)
        self['active_scene_index'] = index

    def get_scene(self):
        return self['active_scene_index'] if 'active_scene_index' in self else -1

    active_scene_index : bpy.props.IntProperty(set=set_scene_and_update, get=get_scene)
    scenes : bpy.props.CollectionProperty(type=Smithy2D_Scene)


def register():
    bpy.types.Object.smithy2d = bpy.props.PointerProperty(type=Smithy2D_Object)
    bpy.types.Scene.smithy2d = bpy.props.PointerProperty(type=Smithy2D_ScenePropertyGroup)
    bpy.types.Image.smithy2d = bpy.props.PointerProperty(type=Smithy2D_Image)

def unregister():
    del bpy.types.Object.smithy2d
    del bpy.types.Scene.smithy2d
    del bpy.types.Image.smithy2d
