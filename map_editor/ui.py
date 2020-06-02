import bpy
from bpy.app.handlers import persistent
from ..utils import * 
from .. import uibase


class Smithy2D_ME_RoomListAction(bpy.types.Operator, uibase.LexBaseListAction):
    bl_idname = "lexlistaction.smithy2d_room_list_action"
    bl_label = "Smithy2D Room List Action"

    def on_execute(self, context):
        if not bpy.data.filepath:
            self.report({"ERROR"}, "Save the project first. This operation needs a project folder.")
            return False
        return True

    def get_collection(self):
        return bpy.context.scene.smithy2d.get_active_scene().rooms

    def get_index_property(self):
        return "active_room_index"

    def get_index_source(self):
        return bpy.context.scene.smithy2d.get_active_scene()
    
    def set_index(self, index, propagate):
        smithy_scene = self.get_index_source()
        if propagate:
            smithy_scene.set_room_and_update(index)
        else:
            smithy_scene.set_room(index)

    def new_item(self):
        scene = bpy.context.scene.smithy2d.get_active_scene()
        room = scene.get_active_room()
        unique_name = get_unique_room_name(scene.name, room.name) if room and self.shift else get_unique_room_name(scene.name, "Room")
        execute_type = "INVOKE_DEFAULT" if not self.shift else "EXEC_DEFAULT"
        bpy.ops.smithy2d.room_adder(execute_type, room_name=unique_name, duplicate=self.shift)

    def remove_item(self, item_idx):
        item = self.get_collection()[item_idx]
        bpy.ops.smithy2d.room_deleter('INVOKE_DEFAULT', datapath=item.path_from_id())


class Smithy2D_ME_RoomVariantListAction(bpy.types.Operator, uibase.LexBaseListAction):
    bl_idname = "lexlistaction.smithy2d_roomvariant_list_action"
    bl_label = "Smithy2D Room Variant List Action"

    def on_execute(self, context):
        if not bpy.data.filepath:
            self.report({"ERROR"}, "Save the project first. This operation needs a project folder.")
            return False
        return True

    def get_collection(self):
        room = bpy.context.scene.smithy2d.get_active_scene().get_active_room()
        return room.variants

    def get_index_property(self):
        return "active_variant_index"

    def set_index(self, index, propagate):
        variants = self.get_index_source()
        if propagate:
            variants.set_variant_and_update(index)
        else:
            variants.set_variant(index)

    def get_index_source(self):
        room = bpy.context.scene.smithy2d.get_active_scene().get_active_room()
        return room

    def new_item(self):
        scene = bpy.context.scene.smithy2d.get_active_scene()
        room = scene.get_active_room()
        variant = room.get_active_variant()
        unique_name = get_unique_variant_name(scene.name, room.name, variant.name) if variant and self.shift else get_unique_variant_name(scene.name, room.name, "Variant")
        execute_type = "INVOKE_DEFAULT" if not self.shift else "EXEC_DEFAULT"
        bpy.ops.smithy2d.variant_adder(execute_type, variant_name=unique_name, duplicate=self.shift)

    def remove_item(self, item_idx):
        item = self.get_collection()[item_idx]
        bpy.ops.smithy2d.variant_deleter('INVOKE_DEFAULT', datapath=item.path_from_id())


class Smithy2D_ME_SceneListAction(bpy.types.Operator, uibase.LexBaseListAction):
    bl_idname = "lexlistaction.smithy2d_scene_list_action"
    bl_label = "Smithy2D Scene List Action"

    def on_execute(self, context):
        if not bpy.data.filepath:
            self.report({"ERROR"}, "Save the project first. This operation needs a project folder.")
            return False
        return True

    def get_collection(self):
        return bpy.context.scene.smithy2d.scenes

    def get_index_property(self):
        return "active_scene_index"

    def get_index_source(self):
        return bpy.context.scene.smithy2d

    def set_index(self, index, propagate):
        if propagate:
            bpy.context.scene.smithy2d.set_scene_and_update(index)
        else:
            bpy.context.scene.smithy2d.set_scene(index)

    def new_item(self):
        scene = bpy.context.scene.smithy2d.get_active_scene()
        unique_name = get_unique_scene_name(scene.name) if scene and self.shift else get_unique_scene_name("Scene")
        execute_type = "INVOKE_DEFAULT" if not self.shift else "EXEC_DEFAULT"
        bpy.ops.smithy2d.scene_adder(execute_type, scene_name=unique_name, duplicate=self.shift)

    def remove_item(self, item_idx):
        item = self.get_collection()[item_idx]
        bpy.ops.smithy2d.scene_deleter('INVOKE_DEFAULT', datapath=item.path_from_id())


class Smithy2D_VariantUIList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        operator = layout.operator("smithy2d.variant_renamer", icon="GREASEPENCIL", text="")
        operator['name'] = item.name
        operator.variant_datapath = item.path_from_id()
        layout.label(text=item.name)

class Smithy2D_RoomUIList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        operator = layout.operator("smithy2d.room_renamer", icon="GREASEPENCIL", text="")
        operator['name'] = item.name
        operator.room_datapath = item.path_from_id()
        layout.label(text=item.name)


class Smithy2D_SceneUIList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        operator = layout.operator("smithy2d.scene_renamer", icon="GREASEPENCIL", text="")
        operator['name'] = item.name
        operator.scene_datapath = item.path_from_id()
        layout.label(text=item.name)


class Smithy2D_MT_variant_list_options(bpy.types.Menu):
    bl_idname = "SMITHY2D_MT_variant_list_options"
    bl_label = "Options"

    @classmethod
    def poll(cls, context):
        scene = context.scene.smithy2d.get_active_scene()
        return scene and scene.get_active_room()

    def draw(self, context):
        layout = self.layout
        scene = context.scene.smithy2d.get_active_scene()
        room = scene.get_active_room()
        variant = room.get_active_variant() 
        assetpath = variant_script_assetpath(scene.name, room.name, variant.name if variant else "_") 
        variant_path = asset_abspath(assetpath)
        layout.operator("smithy2d.show_path_in_explorer", text="Open In Explorer").path = variant_path
        layout.operator("smithy2d.copy_variant_to_clipboard", text="Copy Variant")
        layout.operator("smithy2d.paste_variant_from_clipboard", text="Paste Variant")

class Smithy2D_MT_room_list_options(bpy.types.Menu):
    bl_idname = "SMITHY2D_MT_room_list_options"
    bl_label = "Options"

    @classmethod
    def poll(cls, context):
        scene = context.scene.smithy2d.get_active_scene()
        return scene

    def draw(self, context):
        layout = self.layout
        scene = context.scene.smithy2d.get_active_scene()
        room = scene.get_active_room()
        assetpath = room_dir_assetpath(scene.name, room.name if room else "_") 
        room_path = asset_abspath(assetpath)
        layout.operator("smithy2d.show_path_in_explorer", text="Open In Explorer").path = room_path
        layout.operator("smithy2d.copy_room_to_clipboard", text="Copy Room")
        layout.operator("smithy2d.paste_room_from_clipboard", text="Paste Room")

class Smithy2D_MT_scene_list_options(bpy.types.Menu):
    bl_idname = "SMITHY2D_MT_scene_list_options"
    bl_label = "Options"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout
        scene = context.scene.smithy2d.get_active_scene()
        assetpath = scene_dir_assetpath(scene.name if scene else "_") 
        scene_path = asset_abspath(assetpath)
        layout.operator("smithy2d.show_path_in_explorer", text="Open In Explorer").path = scene_path
        layout.operator("smithy2d.copy_scene_to_clipboard", text="Copy Scene")
        layout.operator("smithy2d.paste_scene_from_clipboard", text="Paste Scene")


class Smithy2D_ME_PT_Scenes(bpy.types.Panel):
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Map'
    bl_options = {'DEFAULT_CLOSED'}
    bl_label = "Scenes"
    
    @classmethod
    def poll(cls, context):
        return context.space_data

    def draw(self, context):
        layout = self.layout

        def draw_list_action(list_idname, action_col, action, icon):
            op = action_col.operator(list_idname, icon=icon, text="")
            op.action = action

        list_row = layout.row()
        list_row.template_list("Smithy2D_SceneUIList", "SmithyScenes",
            context.scene.smithy2d, "scenes",
            context.scene.smithy2d, "active_scene_index",
            rows=3)

        list_action_col = list_row.column(align=True)
        draw_list_action("lexlistaction.smithy2d_scene_list_action", list_action_col, 'ADD', 'ADD')
        draw_list_action("lexlistaction.smithy2d_scene_list_action", list_action_col, 'REMOVE', 'REMOVE')

        if len(context.scene.smithy2d.scenes) > 1:
            draw_list_action("lexlistaction.smithy2d_scene_list_action", list_action_col, 'UP', 'TRIA_UP')
            draw_list_action("lexlistaction.smithy2d_scene_list_action", list_action_col, 'DOWN', 'TRIA_DOWN')
        
        list_action_col.separator()
        list_action_col.operator("wm.call_menu", icon="DOWNARROW_HLT", text="").name = "SMITHY2D_MT_scene_list_options"

        if not bpy.data.filepath:
            layout.enabled = False

class Smithy2D_ME_PT_SceneRooms(bpy.types.Panel):
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Map'
    bl_options = {'DEFAULT_CLOSED'}
    bl_label = "Rooms"
    
    @classmethod
    def poll(cls, context):
        return context.space_data and context.scene.smithy2d.get_active_scene()

    def draw_header(self, context):
        if context.space_data.image:
            self.layout.prop(context.space_data.image.smithy2d, "is_map", text="")

    def draw(self, context):
        layout = self.layout
        smithy_scene = context.scene.smithy2d.get_active_scene()

        def draw_list_action(list_idname, action_col, action, icon):
            op = action_col.operator(list_idname, icon=icon, text="")
            op.action = action

        list_row = layout.row()
        list_row.template_list("Smithy2D_RoomUIList", "SmithyRooms",
                             smithy_scene, "rooms",
                             smithy_scene, "active_room_index",
                             rows=3)

        list_action_col = list_row.column(align=True)
        draw_list_action("lexlistaction.smithy2d_room_list_action", list_action_col, 'ADD', 'ADD')
        draw_list_action("lexlistaction.smithy2d_room_list_action", list_action_col, 'REMOVE', 'REMOVE')

        if len(smithy_scene.rooms) > 1:
            draw_list_action("lexlistaction.smithy2d_room_list_action", list_action_col, 'UP', 'TRIA_UP')
            draw_list_action("lexlistaction.smithy2d_room_list_action", list_action_col, 'DOWN', 'TRIA_DOWN')
        
        list_action_col.separator()
        room = smithy_scene.get_active_room()
        list_action_col.operator("wm.call_menu", icon="DOWNARROW_HLT", text="").name = "SMITHY2D_MT_room_list_options"
        
        if room:
            layout.prop(room, "location", text="Position")
            layout.prop(room, "size", text="Size")

        if not bpy.data.filepath:
            layout.enabled = False

class Smithy2D_ME_PT_SceneRoomVariants(bpy.types.Panel):
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Map'
    bl_options = {'DEFAULT_CLOSED'}
    bl_label = "Variants"

    @classmethod
    def poll(cls, context):
        smithy_scene = context.scene.smithy2d.get_active_scene()
        return (context.space_data 
            and smithy_scene
            and smithy_scene.active_room_index >= 0 
            and smithy_scene.rooms)

    def draw(self, context):
        layout = self.layout
        smithy_scene = context.scene.smithy2d.get_active_scene()
        room = smithy_scene.get_active_room()

        def draw_list_action(list_idname, action_col, action, icon):
            op = action_col.operator(list_idname, icon=icon, text="")
            op.action = action

        list_row = layout.row()
        list_row.template_list("Smithy2D_VariantUIList", "SmithyRoomVariants",
                                room, "variants",
                                room, "active_variant_index",
                                rows=3)

        list_action_col = list_row.column(align=True)
        draw_list_action("lexlistaction.smithy2d_roomvariant_list_action", list_action_col, 'ADD', 'ADD')
        draw_list_action("lexlistaction.smithy2d_roomvariant_list_action", list_action_col, 'REMOVE', 'REMOVE')

        if len(room.variants) > 1:
            draw_list_action("lexlistaction.smithy2d_roomvariant_list_action", list_action_col, 'UP', 'TRIA_UP')
            draw_list_action("lexlistaction.smithy2d_roomvariant_list_action", list_action_col, 'DOWN', 'TRIA_DOWN')
            
        list_action_col.separator()
        list_action_col.operator("wm.call_menu", icon="DOWNARROW_HLT", text="").name = "SMITHY2D_MT_variant_list_options"

        if room.variants:
            layout.operator('smithy2d.edit_selected_room_script', text="Edit Script")
        layout.separator()

        if not bpy.data.filepath:
            layout.enabled = False

def register():
    pass
    
def unregister():
    pass
    