import bpy

class Smithy2D_SM_StateSocket(bpy.types.NodeSocket):
    bl_idname = "Smithy2D_SM_StateSocket"
    bl_label = "State Socket"

    # Optional function for drawing the socket input value
    def draw(self, context, layout, node, text):
        if self.is_linked:
            layout.label(text=text)
        else:
            layout.label(text=text)

    @property
    def connected_nodes(self):
        if not self.is_output:
            if len(self.links) > 0:
                return [self.links[0].from_node]
        else:
            return [l.to_node for l in self.links]

    # Socket color
    def draw_color(self, context, node):
        return (1,1,1,1)

    def check_for_new_input(self):
        assert not self.is_output
        input_node_name = self.links[0].from_node.name if len(self.links) > 0 else ""
        input_node_changed = input_node_name != self.prev_input_node_name
        self.prev_input_node_name = input_node_name
        return input_node_changed

    # properties
    prev_input_node_name : bpy.props.StringProperty()
    


class Smithy2D_SM_BaseStateNode:
    # called when making a new node through the 'add' menu (not called on duplicate)
    def init(self, context):        
        applied_state = self.get_nodegroup().find_applied_state_node()
        if not applied_state:
            # this node will adopt the object's current state
            self.get_nodegroup().set_node_as_applied(self)
        else:
            self.get_nodegroup().apply_state(self)

        self.setup_default_inputs_outputs()
        self.node_created()

    def update(self):
        for i in self.inputs:
            i.check_for_new_input()
        
        # add an extra empty input
        if not self.inputs or self.inputs[-1].is_linked:
            self.inputs.new('Smithy2D_SM_StateSocket', "Previous")
        
        # remove any empty inputs at the end (except for one)
        i = len(self.inputs) - 2
        while i >= 0 and not self.inputs[i].is_linked:
            self.inputs.remove(self.inputs[-1])
            i -= 1

    def setup_default_inputs_outputs(self):
        self.inputs.clear()
        self.outputs.clear()
        self.inputs.new('Smithy2D_SM_StateSocket', "Previous")
        self.outputs.new('Smithy2D_SM_StateSocket', "Continue")
        self.outputs.new('Smithy2D_SM_StateSocket', "Nah")

    def get_input_states(self):
        return []

    def get_output_states(self):
        return []

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == 'Smithy2D_SM_SceneNodeTree'

    def get_nodegroup(self):
        return self.id_data

    def get_receiving_nodes(self):
        receiving_nodes = set()
        for o in self.outputs:
            for link in o.links:
                receiving_nodes.add(link.to_node)
        return receiving_nodes

    # called when a node is duplicated from an existing one
    def copy(self, node):
        self.color = self.true_color
        self.get_nodegroup().apply_state(self)
        self.setup_default_inputs_outputs()
        self.node_created()

    # Free function to clean up on removal.
    def free(self):
        print("Removing node ", self, ", Goodbye!")

    # Additional buttons displayed on the node.
    def draw_buttons(self, context, layout):
        layout.operator("smithy2d.apply_state_node_under_cursor", text="Apply")

    # Detail buttons in the sidebar.
    # If this function is not defined, the draw_buttons function is used instead
    def draw_buttons_ext(self, context, layout):
        layout.prop(self, "lex_name", text="Name")
        layout.prop(self, "true_color", text="Color")

    # called anytime a node is created (either making new or by duplicate)
    def node_created(self):
        default_name = "State"
        name = default_name
        i = 0
        while self.get_nodegroup().nodes.get(name) and self.name != name:
            i += 1
            name = default_name + "_" + str(i)
        
        self.set_lex_name(name)
        self.name = name
        self.label = name

    true_color : bpy.props.FloatVectorProperty(subtype='COLOR', default=(0.4, 0.4, 0.4))
    is_applied : bpy.props.BoolProperty(default=False)


class Smithy2D_SM_BaseNodeTree:
    def set_node_as_applied(self, node):
        applied_state = self.find_applied_state_node()
        if applied_state != node:
            if applied_state:
                applied_state.color = applied_state.true_color
                applied_state.is_applied = False
            
            activated_color = (0.348079, 0.548852, 0.348826)
            node.color = activated_color
            node.use_custom_color = True
            node.is_applied = True
        
        # return the previous applied node
        return applied_state
    
    def find_applied_state_node(self):
        for n in self.nodes:
            if type(n).__name__ == 'Smithy2D_SM_SceneStateNode' and n.is_applied:
                return n
        return None

