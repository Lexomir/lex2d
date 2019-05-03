import bpy
from .node_trees import Smithy2D_SM_BaseNodeTree
import sys

def register():
    lexsuite = sys.modules.get('lex_suite')
    globals()['refresh_screen_area'] = lexsuite.utils.refresh_screen_area

class Smithy2D_SM_SaveObjectState(bpy.types.Operator):
    bl_idname = 'smithy2d.save_object_state'
    bl_label = "Smithy2D Save Object State"

    @classmethod
    def poll(cls, context):
        return context.object

    def execute(self, context):
        obj = context.object

        applied_state_node = obj.smithy2d.get_statemachine().find_applied_state()
        if applied_state_node:
            applied_state_node.save_object_state(obj)
            
            refresh_screen_area("PROPERTIES")

        return {"FINISHED"}

class Smithy2D_SM_LoadObjectState(bpy.types.Operator):
    bl_idname = 'smithy2d.load_object_state'
    bl_label = "Smithy2D Load Object State"

    @classmethod
    def poll(cls, context):
        return context.object

    def execute(self, context):
        obj = context.object

        applied_state_node = obj.smithy2d.get_statemachine().find_applied_state()
        if applied_state_node:
            applied_state_node.load_object_state(obj)

            refresh_screen_area("PROPERTIES")
            
        return {"FINISHED"}


class Smithy2D_SM_ApplySelectedStateNode(bpy.types.Operator):
    bl_idname = 'smithy2d.apply_selected_state_node'
    bl_label = "Smithy2D Apply Selected State Node"

    @classmethod
    def poll(cls, context):
        if not hasattr(context.space_data, "node_tree"):
            return False
            
        node_group = context.space_data.node_tree
        return context.area.type == "NODE_EDITOR" and isinstance(node_group, Smithy2D_SM_BaseNodeTree)
    
    def execute(self, context):
        node_group = context.space_data.node_tree
        if node_group and isinstance(node_group, Smithy2D_SM_BaseNodeTree):
            if node_group.nodes.active:
                print("Applying State:", node_group.nodes.active.name)
                node_group.apply_state(node_group.nodes.active)

        refresh_screen_area("PROPERTIES")

        return {"FINISHED"}

class Smithy2D_SM_ApplyStateNodeUnderCursor(bpy.types.Operator):
    bl_idname = 'smithy2d.apply_state_node_under_cursor'
    bl_label = "Smithy2D Apply State Node Under Cursor"

    @classmethod
    def poll(cls, context):
        if not hasattr(context.space_data, "node_tree"):
            return False
         
        node_group = context.space_data.node_tree
        return context.area.type == "NODE_EDITOR" and isinstance(node_group, Smithy2D_SM_BaseNodeTree)
    
    def invoke(self, context, event):
        node_group = context.space_data.node_tree

        bpy.ops.node.select(mouse_x=event.mouse_region_x, mouse_y=event.mouse_region_y, extend=False)
        bpy.ops.smithy2d.apply_selected_state_node()

        return {"FINISHED"}
