
import bpy
import mathutils
from mathutils import Vector, Matrix, Quaternion
from .utils import *

def update_variant_to_1_0_0(variant):
    def flatten(mat):
        dim = len(mat)
        return [mat[j][i] for i in range(dim) for j in range(dim)]

    for obj_state in variant.object_states:
        loc = Vector(obj_state.location)
        rot = Quaternion(obj_state.rotation_quaternion)
        scale = Vector(obj_state.scale)
        if tuple([scale[0], scale[1], scale[2]]) == (0.0,0.0,0.0):
            print("WARNING: '{}' had a scale of 0. Ignoring object. (Variant '{}' probably didn't need to be updated)".format(obj_state.name, variant.name))
        else:
            mat = rot.to_matrix().to_4x4() @ Matrix.Diagonal(scale).to_4x4()
            mat.translation = loc
            obj_state.matrix_local = flatten(mat)
            dim = obj_state.bounds.get_dimensions()
            obj_state.obj_type = "MESH" if dim[0] != 0 or dim[0] != 0 else "EMPTY"
            obj_state.obj_subtype = "ARROWS"

class Smithy2D_ConvertActiveSceneToAddonVersion(bpy.types.Operator):
    bl_idname = "smithy2d.update_active_scene_to_addon_version"
    bl_label = "Convert Active Scene To Smithy Addon Version"

    @classmethod
    def poll(cls, context):
        scene = context.scene.smithy2d.get_active_scene()
        return scene

    def draw(self, context):
        row = self.layout.row()
        row.prop(self, "old_version", text="File")
        row.prop(self, "new_version", text="Target")
        
        self.layout.separator()
        col = self.layout.column(align=True)
        if addon_has_breaking_changes(self.old_version, self.new_version):
            col.label(text="New version has breaking changes")
            col.label(text="Do you want to update your assets to be compatible?")
        else:
            col.label(text="No breaking changes for this version")
            col.label(text="Nothing to update")

    def execute(self, context):    
        scene = context.scene.smithy2d.get_active_scene()
        print("Updating scene '{}' from Smithy2D Addon version {}.{}.{} to {}.{}.{}".format(room.name, *tuple(self.old_version), *tuple(self.new_version)))
        if version_compare((1, 0, 0), self.old_version) < 0:
            print("-- converting location,scale,rotation properties into matrix_local property")
            for room in scene.rooms:
                for variant in room.variants:
                    update_variant_to_1_0_0(variant)

        # reload the current scene
        room = scene.get_active_room()
        variant = room.get_active_variant() if room else None
        if variant:
            load_state((scene, room, variant))
        return {"FINISHED"}
            
    def invoke(self, context, event):
        self.old_version = context.scene.smithy2d.version
        return context.window_manager.invoke_props_dialog(self, width=400)

    old_version : bpy.props.IntVectorProperty(size=3, default=[-1,-1,-1], soft_min=0, soft_max=99)
    new_version : bpy.props.IntVectorProperty(size=3, default=get_addon_version(), soft_min=0, soft_max=99)

class Smithy2D_ConvertActiveRoomToAddonVersion(bpy.types.Operator):
    bl_idname = "smithy2d.update_active_room_to_addon_version"
    bl_label = "Convert Active Room To Smithy Addon Version"

    @classmethod
    def poll(cls, context):
        scene = context.scene.smithy2d.get_active_scene()
        room = scene.get_active_room() if scene else None
        return room

    def draw(self, context):
        row = self.layout.row()
        row.prop(self, "old_version", text="File")
        row.prop(self, "new_version", text="Target")
        
        self.layout.separator()
        col = self.layout.column(align=True)
        if addon_has_breaking_changes(self.old_version, self.new_version):
            col.label(text="New version has breaking changes")
            col.label(text="Do you want to update your assets to be compatible?")
        else:
            col.label(text="No breaking changes for this version")
            col.label(text="Nothing to update")

    def execute(self, context):    
        scene = context.scene.smithy2d.get_active_scene()
        room = scene.get_active_room()
        print("Updating room '{}' from Smithy2D Addon version {}.{}.{} to {}.{}.{}".format(room.name, *tuple(self.old_version), *tuple(self.new_version)))
        if version_compare((1, 0, 0), self.old_version) < 0:
            print("-- converting location,scale,rotation properties into matrix_local property")
            for variant in room.variants:
                update_variant_to_1_0_0(variant)

        # reload the current room
        variant = room.get_active_variant()
        if variant:
            load_state((scene, room, variant))
        return {"FINISHED"}
            
    def invoke(self, context, event):
        self.old_version = context.scene.smithy2d.version
        return context.window_manager.invoke_props_dialog(self, width=400)

    old_version : bpy.props.IntVectorProperty(size=3, default=[-1,-1,-1], soft_min=0, soft_max=99)
    new_version : bpy.props.IntVectorProperty(size=3, default=get_addon_version(), soft_min=0, soft_max=99)

class Smithy2D_ConvertActiveVariantToAddonVersion(bpy.types.Operator):
    bl_idname = "smithy2d.update_active_variant_to_addon_version"
    bl_label = "Convert Active Variant To Smithy Addon Version"

    @classmethod
    def poll(cls, context):
        scene = context.scene.smithy2d.get_active_scene()
        room = scene.get_active_room() if scene else None
        variant = room.get_active_variant() 
        return variant

    def draw(self, context):
        row = self.layout.row()
        row.prop(self, "old_version", text="File")
        row.prop(self, "new_version", text="Target")
        
        self.layout.separator()
        col = self.layout.column(align=True)
        if addon_has_breaking_changes(self.old_version, self.new_version):
            col.label(text="New version has breaking changes")
            col.label(text="Do you want to update your assets to be compatible?")
        else:
            col.label(text="No breaking changes for this version")
            col.label(text="Nothing to update")

    def execute(self, context):    
        scene = context.scene.smithy2d.get_active_scene()
        room = scene.get_active_room() if scene else None
        variant = room.get_active_variant() 
        print("Updating variant '{}' from Smithy2D Addon version {}.{}.{} to {}.{}.{}".format(variant.name, *tuple(self.old_version), *tuple(self.new_version)))
        if version_compare((1, 0, 0), self.old_version) < 0:
            print("-- converting location,scale,rotation properties into matrix_local property")
            update_variant_to_1_0_0(variant)

        # reload the current variant
        load_state((scene, room, variant))
        return {"FINISHED"}

    def invoke(self, context, event):
        self.old_version = context.scene.smithy2d.version
        return context.window_manager.invoke_props_dialog(self, width=400)

    old_version : bpy.props.IntVectorProperty(size=3, default=[-1,-1,-1], soft_min=0, soft_max=99)
    new_version : bpy.props.IntVectorProperty(size=3, default=get_addon_version(), soft_min=0, soft_max=99)

class Smithy2D_ConvertBlendFileToAddonVersion(bpy.types.Operator):
    bl_idname = "smithy2d.update_assets_to_addon_version"
    bl_label = "Convert BlendFile To Smithy Addon Version"

    def draw(self, context):
        row = self.layout.row()
        row.prop(self, "old_version", text="File")
        row.prop(self, "new_version", text="Target")

        if addon_has_breaking_changes(self.old_version, self.new_version):
            self.layout.label(text="New version has breaking changes")
            self.layout.label(text="Do you want to update your assets to be compatible?")
        else:
            self.layout.label(text="Set the blendfile to version {}.{}.{}?".format(*tuple(self.new_version)))


    def execute(self, context):    
        print("Updating assets from Smithy2D Addon version {}.{}.{} to {}.{}.{}".format(*tuple(self.old_version), *tuple(self.new_version)))
        if version_compare((1, 0, 0), self.old_version) < 0:
            print("-- converting location,scale,rotation properties into matrix_local property")
            for bpy_scene in bpy.data.scenes:
                for scene in bpy_scene.smithy2d.scenes:
                    for room in scene.rooms:
                        for variant in room.variants:
                            update_variant_to_1_0_0(variant)

        # set to the new version
        for bpy_scene in bpy.data.scenes:
            bpy_scene.smithy2d.version = self.new_version

        # reload the current scene
        scene = context.scene.smithy2d.get_active_scene()
        room = scene.get_active_room() if scene else None
        variant = room.get_active_variant() if room else None
        if variant:
            load_state((scene, room, variant))
        return {"FINISHED"}

    def invoke(self, context, event):
        self.old_version = context.scene.smithy2d.version
        return context.window_manager.invoke_props_dialog(self, width=400)

    old_version : bpy.props.IntVectorProperty(size=3, default=[-1,-1,-1], soft_min=0, soft_max=99)
    new_version : bpy.props.IntVectorProperty(size=3, default=get_addon_version(), soft_min=0, soft_max=99)
