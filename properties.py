import bpy
from . import statemachine
from . import ecs
from .utils import *
import time
import sys


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
                self.get_component_system().refresh_inputs(bpy.context.scene, bpy.context.scene.smithy2d.get_active_room(), c)
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
    scene = bpy.data.scenes.get(old_name)
    if scene:
        scene.name = new_name
        old_scene_dir = scene_dir_assetpath(old_name)
        new_scene_dir = scene_dir_assetpath(new_name)
        move_merge_folders(asset_abspath(old_scene_dir), asset_abspath(new_scene_dir))
    else:
        bpy.context.window_manager.smithy2d.ensure_scene_list()

SMITHY2D_INVALID_ID = 0
class Smithy2D_Scene(bpy.types.PropertyGroup):
    def set_name(self, name):
        self.id_data.name = name

    def set_name_and_update(self, name):
        if name != self.id_data.name:
            _rename_smithy2d_scene(self.id_data.name, name)
            self.id_data.name = name
        
    def get_name(self):
        return self.id_data.name

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

    def get_id(self):
        if "id" not in self.keys():
            return SMITHY2D_INVALID_ID
        return self["id"]

    def set_id(self, scene_id):
        self['id'] = scene_id

    def get_index(self):
        scene = self.id_data
        for i, s in enumerate(bpy.data.scenes):
            if s == scene:
                return i
        return None

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

    def get_map_image(self):
        return bpy.data.images.get(self.map_image)

    name : bpy.props.StringProperty(set=set_name_and_update, get=get_name)
    statemachine_name : bpy.props.StringProperty()
    rooms : bpy.props.CollectionProperty(type=ecs.properties.Smithy2D_Room)
    active_room_index : bpy.props.IntProperty(default=-1, get=get_room, set=set_room_and_update)
    map_image : bpy.props.StringProperty()

def _scene_changed(old_scene, new_scene):
        old_room = old_scene.smithy2d.get_active_room() if old_scene else None
        old_variant = old_room.get_active_variant() if old_room else None
        new_room = new_scene.smithy2d.get_active_room() if new_scene else None
        new_variant = new_room.get_active_variant() if new_room else None
        switch_state((old_scene, old_room, old_variant), (new_scene, new_room, new_variant))

class Smithy2D_SceneSelectionItem(bpy.types.PropertyGroup):
    def get_unique_name(self, name):
        final_name = name
        i = 0
        while bpy.data.scenes.get(final_name) and final_name != self.name:
            i += 1
            final_name = name + "_" + str(i)
        
        return final_name

    def set_name_and_update(self, name):
        name = self.get_unique_name(name)
        old_name = self.get_name()
        _rename_smithy2d_scene(old_name, name)
        self['name'] = name

    def set_name(self, name):
        self['name'] = name
        
    def get_name(self):
        return self['name'] if 'name' in self else ""

    name : bpy.props.StringProperty(set=set_name_and_update, get=get_name)

class Smithy2D_WindowManager(bpy.types.PropertyGroup):
    def set_scene_and_update(self, index):
        old_scene = bpy.context.scene
        new_scene_item = self.scenes[index] if index >= 0 and index < len(self.scenes) else None
        new_scene = bpy.data.scenes.get(new_scene_item.name)
        if old_scene != new_scene:
            _scene_changed(old_scene, new_scene)
        self['active_scene_index'] = index

    def set_scene(self, index):
        self['active_scene_index'] = index
        
    def get_scene(self):
        return self['active_scene_index'] if 'active_scene_index' in self else -1
    
    def new_scene(self):
        scene = bpy.data.scenes.new("Scene")
        scene_item = self.scenes.add()
        scene_item.set_name(scene.name)
        return scene
    
    def remove_scene(self, index):
        scene_item = self.scenes[index]
        scene = bpy.data.scenes.get(scene_item.name)
        self.scenes.remove(index)
        if scene:
            bpy.data.scenes.remove(scene)

    def ensure_scene_list(self):
        # INEFFICIENT
        for s in bpy.data.scenes:
            if s.name not in self.scenes:
                scene_item = self.scenes.add()
                scene_item.set_name(s.name)
                print('scene "{}" needed sceneitem "{}"'.format(s.name, scene_item.name))
        for i, s_item in reversed(list(enumerate(self.scenes))):
            if s_item.name not in bpy.data.scenes:
                print('sceneitem "{}" didnt have a scene. Removing.'.format(s_item.name))
                self.scenes.remove(i)

    scenes : bpy.props.CollectionProperty(type=Smithy2D_SceneSelectionItem)
    active_scene_index : bpy.props.IntProperty(default=-1, set=set_scene_and_update, get=get_scene)

def HACK_sanity_check():
    bpy.context.window_manager.smithy2d.ensure_scene_list()
    return .5

def register():
    bpy.app.timers.register(HACK_sanity_check, persistent=True)

    bpy.types.Object.smithy2d = bpy.props.PointerProperty(type=Smithy2D_Object)
    bpy.types.Scene.smithy2d = bpy.props.PointerProperty(type=Smithy2D_Scene)
    bpy.types.Image.smithy2d = bpy.props.PointerProperty(type=Smithy2D_Image)
    bpy.types.WindowManager.smithy2d = bpy.props.PointerProperty(type=Smithy2D_WindowManager)

def unregister():
    if bpy.app.timers.is_registered(HACK_sanity_check):
        bpy.app.timers.unregister(HACK_sanity_check)

    del bpy.types.Object.smithy2d
    del bpy.types.Scene.smithy2d
    del bpy.types.Image.smithy2d
    del bpy.types.WindowManager.smithy2d
