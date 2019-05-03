import bpy
from . import statemachine
from . import ecs


class Smithy2D_Object(bpy.types.PropertyGroup):
    def get_component(self, filepath):
        for c in self.components:
            if c.filepath == filepath:
                return c
    
    def add_component(self, filepath):
        c = self.get_component(filepath)
        if not c:
            c = self.components.add()
            c.filepath = filepath
            self.get_component_system().refresh_inputs(c)
        return c

    def remove_component(self, filepath):
        for i, c in enumerate(reversed(self.components)):
            if c.filepath == filepath:
                self.components.remove(i)

    def get_components(self):
        return self.components[:]

    def get_component_system(self):
        return ecs.component_system
    
    active_component_index : bpy.props.IntProperty(default=-1)
    components : bpy.props.CollectionProperty(type=ecs.properties.Smithy2D_Component)

class Smithy2D_Scene(bpy.types.PropertyGroup):
    statemachine_name : bpy.props.StringProperty()

    def get_statemachine(self):
        return statemachine.get_statemachine(self.get_statemachine_name())

    def get_statemachine_name(self):
        # for some reason blender puts three spaces in the beginning (if you select it with prop_search)
        if self.statemachine_name[:3] == '   ':
            return self.statemachine_name[3:]
        else:
            return self.statemachine_name

def register():
    bpy.types.Object.smithy2d = bpy.props.PointerProperty(type=Smithy2D_Object)
    bpy.types.Scene.smithy2d = bpy.props.PointerProperty(type=Smithy2D_Scene)

def unregister():
    del bpy.types.Object.smithy2d
    del bpy.types.Scene.smithy2d
