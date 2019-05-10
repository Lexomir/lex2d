import bpy
from .node_base import Smithy2D_SM_BaseNodeTree

class Smithy2D_SM_SceneStatePanel(bpy.types.Panel):
    bl_idname = "SCENE_PT_smithy2d_sm_scene_state_panel"
    bl_label = "State Machine"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        smithy2d_scene = scene.smithy2d

        layout.prop_search(smithy2d_scene, "statemachine_name", bpy.data, "node_groups", text="", text_ctxt="", translate=True, icon='NONE')


class Smithy2D_SM_PT_SceneStateNodePanel(bpy.types.Panel):
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Node"
    bl_options = {'DEFAULT_CLOSED'}
    bl_label = "Smithy2D"
    
    @classmethod
    def poll(cls, context):
        node_group = context.space_data.node_tree
        return node_group and isinstance(node_group, Smithy2D_SM_BaseNodeTree) and node_group.nodes.active
        
    def draw(self, context):
        layout = self.layout
        scene = context.scene

        node_group = context.space_data.node_tree
        node = node_group.nodes.active

        layout.prop(node, "lex_name", text="Name")
        layout.operator('smithy2d.edit_selected_room_script', text="Edit Script")


# hide the standard node prop panel if it's a smithy stategraph
@classmethod
def not_scene_state_node_poll(cls, context):
        node_group = context.space_data.node_tree
        return node_group and not isinstance(node_group, Smithy2D_SM_BaseNodeTree) and node_group.nodes.active

original_node_basic_panel_poll = None
def register():
    global original_node_basic_panel_poll
    original_node_basic_panel_poll = bpy.types.NODE_PT_active_node_generic.poll
    bpy.types.NODE_PT_active_node_generic.poll = not_scene_state_node_poll

def unregister():
    global original_node_basic_panel_poll
    if original_node_basic_panel_poll:
        bpy.types.NODE_PT_active_node_generic.poll = original_node_basic_panel_poll