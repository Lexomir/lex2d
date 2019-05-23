import bpy
from bpy.app.handlers import persistent
from ..utils import * 
from .. import uibase


class Smithy2D_ME_RoomListAction(bpy.types.Operator, uibase.LexBaseListAction):
    bl_idname = "lexlistaction.smithy2d_room_list_action"
    bl_label = "Smithy2D Room List Action"

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

    def on_add(self, item):
        item.set_name("Room")
        item.variants.add().set_name("Variant")
        item.set_variant(0)
        item.size = (.2, .2)
        item.location = (.4, .4)
        refresh_screen_area("IMAGE_EDITOR")

class Smithy2D_ME_RoomVariantListAction(bpy.types.Operator, uibase.LexBaseListAction):
    bl_idname = "lexlistaction.smithy2d_roomvariant_list_action"
    bl_label = "Smithy2D Room Variant List Action"

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

    def on_add(self, item):
        item.set_name("Variant")
        item.save_scene_state(bpy.context.scene)


class Smithy2D_ME_SceneListAction(bpy.types.Operator, uibase.LexBaseListAction):
    bl_idname = "lexlistaction.smithy2d_scene_list_action"
    bl_label = "Smithy2D Scene List Action"

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
        item = bpy.context.scene.smithy2d.scenes.add().init("Scene")

        refresh_screen_area("IMAGE_EDITOR")
        return item


class Smithy2D_RoomUIList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.prop(item, "name", text="", emboss=False)

    def invoke(self, context, event):
        pass


class Smithy2D_SceneUIList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.prop(item, "name", text="", emboss=False)


class Smithy2D_ME_PT_Scenes(bpy.types.Panel):
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Map'
    bl_options = {'DEFAULT_CLOSED'}
    bl_label = "Scenes"
    
    @classmethod
    def poll(cls, context):
        return context.space_data and context.space_data.image

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
        list_action_col.separator()

        if len(context.scene.smithy2d.scenes) > 1:
            draw_list_action("lexlistaction.smithy2d_scene_list_action", list_action_col, 'UP', 'TRIA_UP')
            draw_list_action("lexlistaction.smithy2d_scene_list_action", list_action_col, 'DOWN', 'TRIA_DOWN')
        

class Smithy2D_ME_PT_SceneRooms(bpy.types.Panel):
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Map'
    bl_options = {'DEFAULT_CLOSED'}
    bl_label = "Rooms"
    
    @classmethod
    def poll(cls, context):
        return context.space_data and context.space_data.image and context.scene.smithy2d.get_active_scene()

    def draw_header(self, context):
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
        list_action_col.separator()

        if len(smithy_scene.rooms) > 1:
            draw_list_action("lexlistaction.smithy2d_room_list_action", list_action_col, 'UP', 'TRIA_UP')
            draw_list_action("lexlistaction.smithy2d_room_list_action", list_action_col, 'DOWN', 'TRIA_DOWN')

        room = smithy_scene.get_active_room()
        if room:
            layout.prop(room, "location", text="Position")
            layout.prop(room, "size", text="Size")


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
            and context.space_data.image
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
        list_row.template_list("Smithy2D_RoomUIList", "SmithyRoomVariants",
                                room, "variants",
                                room, "active_variant_index",
                                rows=3)

        list_action_col = list_row.column(align=True)
        draw_list_action("lexlistaction.smithy2d_roomvariant_list_action", list_action_col, 'ADD', 'ADD')
        draw_list_action("lexlistaction.smithy2d_roomvariant_list_action", list_action_col, 'REMOVE', 'REMOVE')
        list_action_col.separator()

        if len(room.variants) > 1:
            draw_list_action("lexlistaction.smithy2d_roomvariant_list_action", list_action_col, 'UP', 'TRIA_UP')
            draw_list_action("lexlistaction.smithy2d_roomvariant_list_action", list_action_col, 'DOWN', 'TRIA_DOWN')

        if room.variants:
            layout.operator('smithy2d.edit_selected_room_script', text="Edit Script")
        layout.separator()


def register():
    pass
    
def unregister():
    pass
    