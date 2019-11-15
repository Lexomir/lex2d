import bpy
import uuid
from . import ecs, ObjUtils, dialog_system
from .dialog_system import TEXT_INPUT_PADDING, DIALOG_PADDING, WIDGET_PADDING
from .utils import *
from mathutils import Matrix, Vector
import time
import sys
from bpy.app.handlers import persistent
import blf

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

        def flatten(mat):
            dim = len(mat)
            return [mat[j][i] for i in range(dim) 
                            for j in range(dim)]
        self.matrix_local = flatten(obj.matrix_local)

        self.topleft = ObjUtils.BoundingBox(obj).get_bottombackleft() # bottom back left of the raw data (not scaled)
        self.bounds.set_from_object(obj)
        self.parent = obj.parent.name if obj.parent else ""
        self.obj_type = obj.type

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

        obj.matrix_parent_inverse = Matrix()
        obj.matrix_local = self.matrix_local
        obj.parent = bpy.data.objects.get(self.parent)
        
        if obj.type == "MESH":
            # find the delta vertex movement of object (compare the top left bounding box of both states)
            bounds = ObjUtils.BoundingBox(obj)
            tl = bounds.get_bottombackleft()
            new_tl = Vector(self.topleft)
            vert_move_amt = new_tl - tl
            # shift the object (in order to move it's verts in the right spot), then set the object's origin
            ObjUtils.shift_verts(obj, vert_move_amt)

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

    # deprecated
    location : bpy.props.FloatVectorProperty(size=3)
    scale : bpy.props.FloatVectorProperty(size=3)
    rotation_quaternion : bpy.props.FloatVectorProperty(size=4)
    need_old_stuff : bpy.props.BoolProperty(default=True)

    # properties
    size : bpy.props.FloatVectorProperty(size=3)
    components_serialized : bpy.props.CollectionProperty(type=Smithy2D_SerializedComponent)
    custom_state_data : bpy.props.CollectionProperty(type=Smithy2D_LexStringProperty)
    topleft : bpy.props.FloatVectorProperty(size=3)
    matrix_local : bpy.props.FloatVectorProperty(
        name="Matrix",
        size=16,
        subtype="MATRIX")
    dimensions : bpy.props.FloatVectorProperty(size=3)
    bounds : bpy.props.PointerProperty(type=ObjUtils.BpyBoundingBox)
    parent : bpy.props.StringProperty(default="")
    obj_type : bpy.props.StringProperty(default="MESH")

class Smithy2D_RoomVariant(bpy.types.PropertyGroup):
    def __str__(self):
        room = self.get_room()
        return "{}:{}:{}".format(room.get_scene().name or "_", room.name or "_", self.name or "_")
        
    def get_unique_name(self, name):
        room = self.get_room()
        scene = room.get_scene()
        final_name = name
        i = 0
        found_name = False
        while not found_name and final_name != self.name:
            variant_script_filepath = asset_abspath(room_script_assetpath(scene.name, room.name, final_name))
            if not os.path.exists(variant_script_filepath):
                found_name = True
            else:  
                i += 1
                final_name = name + "_" + str(i)
        
        return final_name
    
    def index(self):
        room = self.get_room()
        for i, v in enumerate(room.variants):
            if v == self:
                return i

    def init(self, name):
        room = self.get_room()
        scene = room.get_scene()
        self.guid = str(uuid.uuid4())
        name = get_unique_variant_name(scene.name, room.name, name)
        variant_script_filepath = asset_abspath(room_script_assetpath(scene.name, room.name, name))
        if not os.path.exists(variant_script_filepath) and create_room_script(scene.name, room.name, name):
            self.set_name(name)
        else:
            print("ERROR: Setting variant name to '{}', but there is already a script file at '{}'".format(name, variant_script_filepath))

    def set_name(self, val):
        self['name'] = val
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
    
    def load_scene_state(self, bpy_scene):
        prev_objects = bpy.data.objects.keys()
        for state in self.object_states:
            obj = get_or_create_object(state.name, state.obj_type)
            move_onstage(obj)
            state.load(obj)
            if obj.name in prev_objects:
                prev_objects.remove(obj.name)
        
        for prev_obj in prev_objects:
            assert prev_obj in bpy.data.objects
            move_backstage(bpy.data.objects.get(prev_obj))

    guid : bpy.props.StringProperty(default="")
    name : bpy.props.StringProperty()
    object_states : bpy.props.CollectionProperty(type=Smithy2D_ObjectState)

class Smithy2D_Room(bpy.types.PropertyGroup):
    def init(self, name):
        scene = self.get_scene()
        name = get_unique_room_name(scene.name, name)
        room_dir_abspath = asset_abspath(room_dir_assetpath(scene.name, name))
        self.guid = str(uuid.uuid4())
        if not os.path.exists(room_dir_abspath):
            self.set_name(name)
        else:
            print("ERROR: Setting room name to '{}', but there is already a directory at '{}'".format(name, room_dir_abspath))
        self.variants.add().init('Variant')
        self.set_variant(0)
        self.size = (.2, .2)
        self.location = (.4, .4)
        return self

    def __str__(self):
        return "{}:{}".format(self.get_scene().name or "_", self.name or "_")

    def get_unique_name(self, name):
        scene = self.get_scene()
        final_name = name
        i = 0
        found_name = False
        while not found_name and final_name != self.name:
            room_dir_abspath = asset_abspath(room_dir_assetpath(scene.name, final_name))
            if not os.path.exists(room_dir_abspath):
                found_name = True
            else:  
                i += 1
                final_name = name + "_" + str(i)
        return final_name

    def index(self):
        scene = self.get_scene()
        for i, r in enumerate(scene.rooms):
            if r == self:
                return i

    def set_name(self, val):
        self['name'] = val
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

    def load_variant(self, index, force=False):
        variant = self.variants[index] if self.variants and index >= 0 else None
        if not variant or (variant == self.get_active_variant() and not force):
            return 
        if variant:
            load_state((self.get_scene(), self, variant))

    def set_variant(self, index):
        self['active_variant_index'] = index

    def get_variant(self):
        return self.get('active_variant_index', -1)

    def set_variant_and_update(self, index):
        if index == self.active_variant_index: return
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

    guid : bpy.props.StringProperty(default="")
    location : bpy.props.FloatVectorProperty(size=2)
    size : bpy.props.FloatVectorProperty(size=2)
    variants : bpy.props.CollectionProperty(type=Smithy2D_RoomVariant)
    active_variant_index: bpy.props.IntProperty(default=-1, set=set_variant_and_update, get=get_variant)
    name : bpy.props.StringProperty()

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

SMITHY2D_INVALID_ID = 0
class Smithy2D_Scene(bpy.types.PropertyGroup):
    def __str__(self):
        return self.name or "_"
        
    def init(self, name):
        name = get_unique_scene_name(name)
        scene_dir_abspath = asset_abspath(scene_dir_assetpath(name))
        self.guid = str(uuid.uuid4())
        if not os.path.exists(scene_dir_abspath):
            self.set_name(name)
        else:
            print("ERROR: Setting scene name to '{}', but there is already a directory at '{}'".format(name, scene_dir_abspath))

        room = self.rooms.add().init("Room")
        self.set_room(0)

        return self

    def get_unique_name(self, name):
        final_name = name
        i = 0
        found_name = False
        while not found_name and final_name != self.name:
            scene_dir_abspath = asset_abspath(scene_dir_assetpath(final_name))
            if not os.path.exists(scene_dir_abspath):
                found_name = True
            else:  
                i += 1
                final_name = name + "_" + str(i)
        
        return final_name

    def set_name(self, name):
        self['name'] = name
        refresh_screen_area("PROPERTIES")
        
    def get_name(self):
        return self['name'] if 'name' in self else ''

    def load_room(self, index, force=False):
        room = self.rooms[index] if self.rooms and index >= 0 else None
        if not room or (room == self.get_active_room() and not force):
            return 
        variant = room.get_active_variant() if room else None
        if variant:
            load_state((self, room, variant))

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

    guid : bpy.props.StringProperty(default="")
    name : bpy.props.StringProperty()
    rooms : bpy.props.CollectionProperty(type=Smithy2D_Room)
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

    def load_scene(self, index, force=False):
        new_scene = self.scenes[index] if self.scenes and index >= 0 else None
        if not new_scene or (new_scene == self.get_active_scene() and not force):
            return 

        new_room = new_scene.get_active_room() if new_scene else None
        new_variant = new_room.get_active_variant() if new_room else None
        if new_variant:
            load_state((new_scene, new_room, new_variant))

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
