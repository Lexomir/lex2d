import bpy
import subprocess
import sys
import os
from . import uibase, ecs
from .utils import *

class Smithy2D_ComponentListAction(bpy.types.Operator, uibase.LexBaseListAction):
    bl_idname = "lexlistaction.smithy2d_component_list_action"
    bl_label = "Smithy2D Component List Action"

    def get_collection(self):
        return bpy.context.object.smithy2d.components

    def get_index_property(self):
        return "active_component_index"

    def get_index_source(self):
        return bpy.context.object.smithy2d

    def on_add(self, item):
        pass


class Smithy2D_ComponentUIList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()
        row.prop(item, "name", text="", emboss=False)
        row.prop(item, "is_global", text="", emboss=True)

    def invoke(self, context, event):
        i = "sup"


class Smithy2D_ScenePanel(bpy.types.Panel):
    bl_idname = "SCENE_PT_lex_game_scene_panel"
    bl_label = "Smithy2D"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    @classmethod
    def poll(cls, context):
        return context.scene

    def draw(self, context):
        layout = self.layout
        room = context.scene.smithy2d.get_active_room()
        variant = room.get_active_variant() if room else None
        if room and variant:
            layout.label(text="{} ({})".format(room.name, variant.name))
            layout.operator('smithy2d.edit_selected_room_script', text="Edit Script")
        else:
            layout.label(text="State: [None]")



class Smithy2D_GameObjectPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_smithy2d_obj_panel"
    bl_label = "Smithy2D Components"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    @classmethod
    def poll(cls, context):
        return context.object

    def draw(self, context):
        layout = self.layout
        obj = context.object
        smithy_obj = obj.smithy2d
        
        def draw_list_action(list_idname, action_col, action, icon):
            op = action_col.operator(list_idname, icon=icon, text="")
            op.action = action

        list_row = layout.row()
        list_row.template_list("Smithy2D_ComponentUIList", "SmithyComponents",
                             smithy_obj, "components",
                             smithy_obj, "active_component_index",
                             rows=3)

        list_action_row = list_row.column(align=True)
        draw_list_action("lexlistaction.smithy2d_component_list_action", list_action_row, 'ADD', 'ADD')
        draw_list_action("lexlistaction.smithy2d_component_list_action", list_action_row, 'REMOVE', 'REMOVE')
        list_action_row.separator()

        if len(smithy_obj.components) > 1:
            draw_list_action("lexlistaction.smithy2d_component_list_action", list_action_row, 'UP', 'TRIA_UP')
            draw_list_action("lexlistaction.smithy2d_component_list_action", list_action_row, 'DOWN', 'TRIA_DOWN')

        if smithy_obj.active_component_index >= 0  and smithy_obj.active_component_index < len(smithy_obj.components):
            c = smithy_obj.components[smithy_obj.active_component_index]

            # component editing
            component_layout = layout.box() if len(c.inputs) > 0 else layout

            if c.file_exists:
                file_action_row = component_layout.row(align=True).split(factor=.25)
                file_action_row.operator("smithy2d.open_component_script_external", text="Open")
            else:
                if not context.scene.smithy2d.get_active_room() and not c.is_global:
                    component_layout.label(text="Non-global components need a room")
                room = context.scene.smithy2d.get_active_room()
                variant = room.get_active_variant() if room else None
                file_action_row = component_layout.row(align=True).split(factor=.3)
                file_action_row.operator("smithy2d.new_component_script", icon="ADD", text="Create")

            # component properties
            if c.valid():
                for c_input in c.inputs:
                    c_input.draw(component_layout, context)
            else:
                component_layout.label(text=c.err_log)

        layout.separator()


class Smithy2D_OpenComponentScriptExternal(bpy.types.Operator):
    bl_idname = 'smithy2d.open_component_script_external'
    bl_label = "Edit Smithy2D Component Script"
    
    @classmethod
    def poll(self, context):
        c_index = context.object.smithy2d.active_component_index
        c = None
        if 0 <= c_index < len(context.object.smithy2d.components):
            c = context.object.smithy2d.components[c_index]
        return context.object and c and c.name != ""

    def execute(self, context):
        if not bpy.data.filepath:
            self.report({"ERROR"}, "Save the project first. This operation needs a project folder.")
            return {"CANCELLED"}

        c_index = context.object.smithy2d.active_component_index
        c = context.object.smithy2d.components[c_index]
        
        room = context.scene.smithy2d.get_active_room()
        if not room and not c.is_global:
            return {"FINISHED"}

        script_filepath = asset_abspath(c.get_assetpath(context.scene, room))
        subprocess.run(['code', os.path.dirname(script_filepath), script_filepath], shell=True)

        return {"FINISHED"}


class Smithy2D_NewComponentScript(bpy.types.Operator):
    bl_idname = 'smithy2d.new_component_script'
    bl_label = "New Smithy2D Component Script"

    script_name : bpy.props.StringProperty(default="")

    @classmethod
    def poll(self, context):
        c_index = context.object.smithy2d.active_component_index
        if 0 <= c_index < len(context.object.smithy2d.components):
            c = context.object.smithy2d.components[c_index]
        return context.object and c and c.name != "" and (context.scene.smithy2d.get_active_room() or c.is_global)

    def execute(self, context):
        if not bpy.data.filepath:
            self.report({"ERROR"}, "Save the project first. This operation needs a project folder.")
            return {"CANCELLED"}
            
        def create_component_script(bpy_component):
            template_filepath = os.path.abspath(os.path.dirname(__file__) + "/ecs/templates/smithy_component_template.txt")
            with open(template_filepath, "r") as template_file:
                component_template = template_file.read()
            
            output_filepath = asset_abspath(bpy_component.get_assetpath(context.scene, context.scene.smithy2d.get_active_room()))

            os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
            print("Making component: ", output_filepath)

            with open(output_filepath, "w") as script_file:
                component_name = bpy_component.name
                parsed_template = component_template.replace("${COMPONENT_NAME}", component_name)
                script_file.write(parsed_template)
            
            return component_name

        c_index = context.object.smithy2d.active_component_index
        if c_index >= 0:
            c = context.object.smithy2d.components[c_index]
            create_component_script(c)
            ecs.get_component_system().refresh_inputs(c)
            bpy.ops.smithy2d.open_component_script_external()
        return {"FINISHED"}
