import bpy
from .node_base import Smithy2D_SM_BaseNodeTree, Smithy2D_SM_BaseStateNode
from .properties import Smithy2D_SM_ObjectState

import nodeitems_utils
from nodeitems_utils import NodeCategory, NodeItem

def _on_rename_statescript(state_node, old_name, name):
    if not bpy.data.filepath:
        state_node.name = name
        state_node.label = name
        return

    final_name = name
    nodegroup = state_node.get_nodegroup()
    i = 0
    while nodegroup.nodes.get(final_name) and final_name != state_node.name:
        i += 1
        final_name = name + "_" + str(i)
    
    state_node.set_lex_name(final_name)
    state_node.name = final_name
    state_node.label = final_name

    if final_name == old_name:
        return

    # rename script file
    old_script_filepath = abs_state_scriptpath(old_name)
    if os.path.exists(old_script_filepath):
        new_script_filepath = abs_state_scriptpath(final_name)

        if os.path.exists(new_script_filepath):
            os.remove(new_script_filepath)
        os.rename(old_script_filepath, new_script_filepath)


class Smithy2D_SM_SceneStateNode(bpy.types.Node, Smithy2D_SM_BaseStateNode):
    bl_idname = "Smithy2D_SM_SceneStateNode"
    bl_label = "State"
    bl_icon = 'NONE'

    def save_scene_state(self, scene):
        self.object_states.clear()

        objs = bpy.data.objects
        for o in objs:
            state = self.object_states.add()
            state.name = o.name
            state.save(o)
    
    def load_scene_state(self, scene):
        for state in self.object_states:
            obj = bpy.data.objects.get(state.name, None)
            if obj:
                state.load(obj)

    def set_lex_name_and_update(self, val):
        from .. import _scene_state_namechange_callbacks
        old_name = self.get('lex_name', self.name)
        self['lex_name'] = val
        
        _on_rename_statescript(self, old_name, val)

    def set_lex_name(self, val):
        self['lex_name'] = val

    def get_lex_name(self):
        return self.get('lex_name')

    lex_name : bpy.props.StringProperty(set=set_lex_name_and_update, get=get_lex_name)
    object_states : bpy.props.CollectionProperty(type=Smithy2D_SM_ObjectState)
    

class Smithy2D_SM_SceneNodeTree(bpy.types.NodeTree, Smithy2D_SM_BaseNodeTree):
    bl_description = "Smithy2D State Machine"
    bl_icon = "MESH_TORUS"
    bl_idname = "Smithy2D_SM_SceneNodeTree"
    bl_label = "Smithy2D State Machine"

    def find_affected_scenes(self):
        return [s for s in bpy.data.scenes if s.smithy2d.get_statemachine_name() == self.name]

    def save_current_state(self):
        applied_node = self.find_applied_state_node()
        if not applied_node:
            return

        scenes = self.find_affected_scenes()
        if not scenes: 
            return 

        # find source scene
        source_scene = scenes[0]
        for s in scenes:
            if s == bpy.context.scene:
                source_scene = s
                break

        # save the current state of the source scene
        applied_node.save_scene_state(source_scene)


    def apply_state(self, node):
        previously_applied_node = self.set_node_as_applied(node)

        scenes = self.find_affected_scenes()
        if not scenes: 
            return 

        # save state
        if previously_applied_node:
            # find source scene
            source_scene = scenes[0]
            for s in scenes:
                if s == bpy.context.scene:
                    source_scene = s
                    break

            # save the current state of the source scene
            previously_applied_node.save_scene_state(source_scene)

        # load new state
        for s in scenes:
            node.load_scene_state(s)

class Smithy2D_SM_SceneNodeCategory(NodeCategory):
    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == "Smithy2D_SM_SceneNodeTree"



node_categories = [
    Smithy2D_SM_SceneNodeCategory("SCENE", "Main", items = [
        NodeItem("Smithy2D_SM_SceneStateNode"),
    ]),
]
    

def register():
    nodeitems_utils.register_node_categories("Smithy2D_SM_NODES", node_categories)
    

def unregister():
    nodeitems_utils.unregister_node_categories("Smithy2D_SM_NODES")