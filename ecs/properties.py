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

class Smithy2D_LexStringProperty(bpy.types.PropertyGroup):
    value : bpy.props.StringProperty()

class Smithy2D_SerializedComponent(bpy.types.PropertyGroup):
    name : bpy.props.StringProperty()
    is_global : bpy.props.BoolProperty(default=False)
    data : bpy.props.StringProperty()

    def get_assetpath(self, scene, room):
        if self.is_global:
            return global_component_assetpath(self.name)
        else:
            return component_assetpath(self.name, scene.name, room.name)

    def serialize(self, bpy_component_instance):
        self.name = bpy_component_instance.name
        self.is_global = bpy_component_instance.is_global
        serialized_inputs = ""
        for i in bpy_component_instance.inputs:
            serialized_inputs += i.name + "," + i.datatype + "," + i._get_string_value() + "\n"

        self.data = serialized_inputs[:-1]  # without last '\n'

    def deserialize(self, bpy_component_instance):
        serialized_inputs = self.data
        if not serialized_inputs:
            return 

        input_strs = serialized_inputs.split('\n')
        
        c = bpy_component_instance
        c.set_name(self.name)
        c.set_is_global(self.is_global)
        c.inputs.clear()
        for input_str in input_strs:
            name, datatype, str_value = input_str.split(",", 2)
            ci = c.inputs.add()
            ci.name = name
            ci.datatype = datatype
            ci._set_string_value(str_value)

class Smithy2D_ObjectState(bpy.types.PropertyGroup):
    def get_name(self):
        return self.name

    def get_variant(self):
        bpy_scene = self.id_data
        room = bpy_scene.path_resolve(".".join(self.path_from_id().split('.')[0:-1]))
        return room

    # save object state
    def save(self, obj):
        self.components_serialized.clear()
        for c in obj.smithy2d.components:
            if c.name:
                sc = self.components_serialized.add()
                sc.serialize(c)

        self.location = obj.location
        self.topleft = ObjUtils.BoundingBox(obj).get_bottombackleft() # doesnt account for scale
        self.rotation_quaternion = obj.rotation_quaternion
        self.scale = obj.scale
        self.bounds.set_from_object(obj)
        self.parent = obj.parent.name if obj.parent else ""

    # load state into the given object
    def load(self, obj):
        room = self.get_variant().get_room()
        scene = room.get_scene()
        component_system = obj.smithy2d.get_component_system()
        obj.smithy2d.components.clear()
        for new_sc in self.components_serialized:
            bpy_c = obj.smithy2d.add_component(new_sc.name, is_global=new_sc.is_global, calc_inputs=False)
            new_sc.deserialize(bpy_c)
            component_system.refresh_inputs(scene, room, bpy_c)

        if obj.type == "MESH":
            # find the delta vertex movement of object (compare the top left bounding box of both states)
            bounds = ObjUtils.BoundingBox(obj)
            tl = obj.location + multiply_vec3(bounds.get_bottombackleft(), obj.scale)
            new_tl = Vector(self.location) + multiply_vec3(self.topleft, self.scale)
            vert_move_amt = new_tl - tl
            # shift the object (in order to move it's verts in the right spot), then set the object's origin
            obj.location += vert_move_amt
            obj.scale = self.scale
            ObjUtils.set_origin(obj, Vector(self.location))
        else:
            obj.scale = self.scale
            obj.location = self.location

        obj.rotation_quaternion = self.rotation_quaternion
        obj.parent = bpy.data.objects.get(self.parent)

    def store_data(self, identifier, str_data):
        data = self.custom_state_data.get(identifier)
        if not data:
            data = self.custom_state_data.add()
            data.name = identifier
        data.value = str_data

    def get_data(self, identifier):
        data = self.custom_state_data.get(identifier)
        if data:
            return data.value
        return None

    components_serialized : bpy.props.CollectionProperty(type=Smithy2D_SerializedComponent)
    custom_state_data : bpy.props.CollectionProperty(type=Smithy2D_LexStringProperty)
    location : bpy.props.FloatVectorProperty(size=3)
    topleft : bpy.props.FloatVectorProperty(size=3)
    scale : bpy.props.FloatVectorProperty(size=3)
    dimensions : bpy.props.FloatVectorProperty(size=3)
    bounds : bpy.props.PointerProperty(type=ObjUtils.BpyBoundingBox)
    rotation_quaternion : bpy.props.FloatVectorProperty(size=4)
    parent : bpy.props.StringProperty(default="")

def _rename_room_script(variant, old_name, name):
    print("Renaming roomscript  '{}' to '{}'".format(old_name, name))
    # rename variant script file
    scene = variant.get_room().get_scene()
    old_script_assetpath = room_script_assetpath(scene.name, variant.get_room().name, old_name)
    old_script_filepath = asset_abspath(old_script_assetpath)
    if os.path.exists(old_script_filepath):
        new_script_assetpath = room_script_assetpath(scene.name, variant.get_room().name, name)
        new_script_filepath = asset_abspath(new_script_assetpath)

        if os.path.exists(new_script_filepath):
            os.remove(new_script_filepath)
        os.rename(old_script_filepath, new_script_filepath)

class Smithy2D_RoomVariant(bpy.types.PropertyGroup):
    def get_unique_name(self, name):
        room = self.get_room()
        final_name = name
        i = 0
        while room.variants.get(final_name) and final_name != self.name:
            i += 1
            final_name = name + "_" + str(i)
        
        return final_name
    
    def index(self):
        room = self.get_room()
        for i, v in enumerate(room.variants):
            if v == self:
                return i

    def set_name_and_update(self, val):
        old_name = self.get('name', self.name)
        name = self.get_unique_name(val)
        self['name'] = name
        refresh_screen_area("PROPERTIES")
        
        if bpy.data.filepath and name != old_name:
            _rename_room_script(self, old_name, name)

    def set_name(self, val):
        name = self.get_unique_name(val)
        self['name'] = name
        refresh_screen_area("PROPERTIES")

    def get_name(self):
        return self.get('name', "")

    def get_room(self):
        bpy_scene = self.id_data
        room = bpy_scene.path_resolve(".".join(self.path_from_id().split('.')[0:-1]))
        return room

    def save_scene_state(self, bpy_scene):
        self.object_states.clear()

        objs = bpy_scene.objects
        for o in objs:
            if not is_backstage(o):
                state = self.object_states.add()
                state.name = o.name
                state.save(o)
    
    def load_scene_state(self, bpy_sceneC):
        prev_objects = bpy.data.objects.keys()
        for state in self.object_states:
            obj = get_or_create_meshobject(state.name)
            move_onstage(obj)
            state.load(obj)
            if obj.name in prev_objects: 
                prev_objects.remove(obj.name)
        
        for prev_obj in prev_objects:
            assert prev_obj in bpy.data.objects
            move_backstage(bpy.data.objects.get(prev_obj))

    name : bpy.props.StringProperty(set=set_name_and_update, get=get_name)
    object_states : bpy.props.CollectionProperty(type=Smithy2D_ObjectState)

def _rename_room_directory(room, scene_name, old_name, name):
    # rename variant script file
    print("Renaming room directory '{}' to '{}'".format(old_name, name))
    old_room_dir_assetpath = room_dir_assetpath(scene_name, old_name)
    old_room_dir_abspath = asset_abspath(old_room_dir_assetpath)
    if os.path.exists(old_room_dir_abspath):
        new_room_dir_assetpath = room_dir_assetpath(scene_name, name)
        new_room_dir_abspath = asset_abspath(new_room_dir_assetpath)
        move_merge_folders(old_room_dir_abspath, new_room_dir_abspath)

class Smithy2D_Room(bpy.types.PropertyGroup):
    def init(self, name):
        self.set_name(name)
        self.variants.add().set_name('Variant')
        self.set_variant(0)
        self.size = (.2, .2)
        self.location = (.4, .4)
        return self

    def get_unique_name(self, name):
        scene = self.get_scene()
        final_name = name
        i = 0
        while scene.rooms.get(final_name) and final_name != self.name:
            i += 1
            final_name = name + "_" + str(i)
        
        return final_name

    def set_name_and_update(self, val):
        old_name = self.get('name', self.name)
        name = self.get_unique_name(val)
        self['name'] = name
        refresh_screen_area("PROPERTIES")
        
        scene = self.get_scene()
        if bpy.data.filepath and name != old_name:
            _rename_room_directory(self, scene.name, old_name, name)

    def index(self):
        scene = self.get_scene()
        for i, r in enumerate(scene.rooms):
            if r == self:
                return i

    def set_name(self, val):
        name = self.get_unique_name(val)
        self['name'] = name
        refresh_screen_area("PROPERTIES")

    def get_name(self):
        return self.get('name', "")

    def get_scene(self):
        bpy_scene = self.id_data
        scene = bpy_scene.path_resolve(".".join(self.path_from_id().split('.')[0:-1]))
        return scene

    def contains(self, point):
        return (point[0] >= self.location[0] and point[0] <= (self.location[0] + self.size[0]) 
            and point[1] >= self.location[1] and point[1] <= (self.location[1] + self.size[1]))
    
    def get_active_variant(self):
        if self.active_variant_index >= 0 and self.variants:
            return self.variants[self.active_variant_index]
        return None

    def set_variant(self, index):
        self['active_variant_index'] = index

    def get_variant(self):
        return self.get('active_variant_index', -1)

    def set_variant_and_update(self, index):
        variant = self.variants[index] if index >= 0 else None
        if variant:
            room = variant.get_room() if variant else None
            scene = room.get_scene() if room else None

            old_index = self.active_variant_index
            old_variant = self.variants[old_index] if old_index >= 0 and old_index != index else None
            old_scene = old_variant.get_room().get_scene() if old_variant else None
            old_room = old_variant.get_room() if old_variant else None
            switch_state((old_scene, old_room, old_variant),
                        (scene, room, variant))
        self['active_variant_index'] = index

    location : bpy.props.FloatVectorProperty(size=2)
    size : bpy.props.FloatVectorProperty(size=2)
    variants : bpy.props.CollectionProperty(type=Smithy2D_RoomVariant)
    active_variant_index: bpy.props.IntProperty(default=-1, set=set_variant_and_update, get=get_variant)
    name : bpy.props.StringProperty(set=set_name_and_update, get=get_name)