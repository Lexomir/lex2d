import bpy
import bpy.app.handlers
from bpy.app.handlers import persistent
import os
import gpu
import bgl
from gpu_extras.batch import batch_for_shader
from ..utils import *


vertices = (
    (0, 1), # tl
    (0, 0), # bl
    (1, 0), # br
    (1, 1)) # tr

indices = (
    (0, 1, 2), (2, 3, 0))

def get_vertex_shader():
    vert_filepath = os.path.normpath(os.path.abspath(os.path.dirname(__file__) + "/room_shader.vert"))
    with open(vert_filepath, "r") as vert_file:
        vert_shader = vert_file.read()
    return vert_shader

def get_fragment_shader():
    frag_filepath = os.path.normpath(os.path.abspath(os.path.dirname(__file__) + "/room_shader.frag"))
    with open(frag_filepath, "r") as frag_file:
        frag_shader = frag_file.read()
    return frag_shader

room_shader = gpu.types.GPUShader(get_vertex_shader(), get_fragment_shader())
room_batch = batch_for_shader(room_shader, 'TRIS', {"pos": vertices}, indices=indices)
_room_draw_handle = None
_mouse_view_location = (0, 0)
_editor_area = None

def is_map_editor(area):
    return (area.type == "IMAGE_EDITOR" 
        and area.spaces.active.image
        and area.spaces.active.image.smithy2d.is_map)

def draw_rooms():
    scene = bpy.context.scene.smithy2d.get_active_scene()
    if is_map_editor(bpy.context.area) and scene:
        room_shader.bind()
        room_shader.uniform_float("MousePos", _mouse_view_location)
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
        for i, room in enumerate(scene.rooms):
            room_shader.uniform_float("RoomPosition", (room.location[0], room.location[1]))
            room_shader.uniform_float("RoomSize", (room.size[0], room.size[1]))
            room_shader.uniform_int("IsSelected", int(i == scene.active_room_index))
            room_batch.draw(room_shader)


class Smithy2D_DrawNewRoom(bpy.types.Operator):
    bl_idname = "smithy2d.draw_new_room"
    bl_label = "Smithy2D: Draw New Room"

    room_index : bpy.props.IntProperty(default=0)
    start_pos : bpy.props.FloatVectorProperty(size=2)

    @classmethod
    def poll(cls, context):
        return context.space_data.type == "IMAGE_EDITOR"
    
    def execute(self, context):
        context.window_manager.modal_handler_add(self)
        scene = context.scene.smithy2d.get_active_scene()
        scene.rooms.add()
        self.room_index = len(scene.rooms) - 1

        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        print("IN THE MODAL")
        return {'FINISHED'}

class Smithy2D_RoomSelector(bpy.types.Operator):
    bl_idname = "smithy2d.select_room"
    bl_label = "Smithy2D: Begin room selector"

    @classmethod
    def poll(cls, context):
        return True
        
    def execute(self, context):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        scene = bpy.context.scene.smithy2d.get_active_scene()
        global _mouse_view_location
        global _editor_area
        if event.type == 'MOUSEMOVE':
            editor_areas = [area for area in bpy.context.screen.areas if is_map_editor(area)]
            _editor_area = None
            for area in editor_areas:
                region = area.regions[-1]
                region_x = event.mouse_x - region.x
                region_y = event.mouse_y - region.y
                if region_x >= 0 and region_x <= region.width and region_y >= 0 and region_y <= region.height:
                    _mouse_view_location = region.view2d.region_to_view(region_x, region_y)
                    _editor_area = area
                    break
            for area in editor_areas:
                area.tag_redraw()
        if event.type == 'RIGHTMOUSE' and event.value == "PRESS":
            editor_areas = [area for area in bpy.context.screen.areas if is_map_editor(area)]
            _editor_area = None
            for area in editor_areas:
                region = area.regions[-1]
                region_x = event.mouse_x - region.x
                region_y = event.mouse_y - region.y
                if region_x >= 0 and region_x <= region.width and region_y >= 0 and region_y <= region.height:
                    _mouse_view_location = region.view2d.region_to_view(region_x, region_y)
                    _editor_area = area
                    for i, room in enumerate(scene.rooms):
                        if room.contains(_mouse_view_location):
                            scene.active_room_index = i
                            break
        if not _editor_area:
            _mouse_view_location = (-1, -1)

        return {'PASS_THROUGH'}
 
class Smithy2D_GrabRoom(bpy.types.Operator):
    bl_idname = 'smithy2d.grab_room'
    bl_label = "Smithy2D Grab/Move Room in map editor"

    start_mousepos : bpy.props.FloatVectorProperty(size=2)
    start_roompos : bpy.props.FloatVectorProperty(size=2)

    @classmethod
    def poll(cls, context):
        area = context.area
        return (area.type == "IMAGE_EDITOR" 
            and area.spaces.active.image
            and area.spaces.active.image.smithy2d.is_map
            and context.scene.smithy2d.get_active_scene()
            and context.scene.smithy2d.get_active_scene().get_active_room())
    
    def invoke(self, context, event):
        scene = context.scene.smithy2d.get_active_scene()
        room = scene.get_active_room()
        self.start_mousepos = context.region.view2d.region_to_view(event.mouse_region_x, event.mouse_region_y)
        self.start_roompos = (room.location[0], room.location[1])
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        scene = context.scene.smithy2d.get_active_scene()
        room = scene.get_active_room()
        if event.type == 'MOUSEMOVE':
            move_ratio = 1
            mousepos = context.region.view2d.region_to_view(event.mouse_region_x, event.mouse_region_y)
            mouse_delta = (mousepos[0] - self.start_mousepos[0], mousepos[1] - self.start_mousepos[1])
            room.location = (self.start_roompos[0] + mouse_delta[0]*move_ratio, self.start_roompos[1] + mouse_delta[1]*move_ratio)
            refresh_screen_area("IMAGE_EDITOR")
        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            return {'FINISHED'}
        elif event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            room.location = (self.start_roompos[0], self.start_roompos[1])
            refresh_screen_area("IMAGE_EDITOR")
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

class Smithy2D_ScaleRoom(bpy.types.Operator):
    bl_idname = 'smithy2d.scale_room'
    bl_label = "Smithy2D Scale Room in map editor"

    start_roompos : bpy.props.FloatVectorProperty(size=2)
    start_roomscale : bpy.props.FloatVectorProperty(size=2)
    start_mousepos : bpy.props.FloatVectorProperty(size=2)

    @classmethod
    def poll(cls, context):
        area = context.area
        return (area.type == "IMAGE_EDITOR" 
            and area.spaces.active.image
            and area.spaces.active.image.smithy2d.is_map
            and context.scene.smithy2d.get_active_scene()
            and context.scene.smithy2d.get_active_scene().get_active_room())
    
    def invoke(self, context, event):
        scene = context.scene.smithy2d.get_active_scene()
        room = scene.get_active_room()
        self.start_roompos = (room.location[0], room.location[1])
        self.start_roomscale = (room.size[0], room.size[1])
        self.start_mousepos = context.region.view2d.region_to_view(event.mouse_region_x, event.mouse_region_y)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        scene = context.scene.smithy2d.get_active_scene()
        room = scene.get_active_room()
        if event.type == 'MOUSEMOVE':
            half_roomscale = (room.size[0] * .5, room.size[1] * .5)
            roomcenter = (room.location[0] + half_roomscale[0], room.location[1] + half_roomscale[1])
            move_ratio = 1
            mousepos = context.region.view2d.region_to_view(event.mouse_region_x, event.mouse_region_y)
            mouse_offset = (mousepos[0] - self.start_mousepos[0], mousepos[1] - self.start_mousepos[1])
            room.size = (self.start_roomscale[0] + mouse_offset[0]*move_ratio, self.start_roomscale[1] + mouse_offset[1]*move_ratio)
            room.location = (roomcenter[0] - room.size[0]*.5, roomcenter[1] - room.size[1]*.5)
            refresh_screen_area("IMAGE_EDITOR")
        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            return {'FINISHED'}
        elif event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            room.location = (self.start_roompos[0], self.start_roompos[1])
            room.size = (self.start_roomscale[0], self.start_roomscale[1])
            refresh_screen_area("IMAGE_EDITOR")
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}


@persistent
def _on_blendfile_load(dummy):
    bpy.ops.smithy2d.select_room('INVOKE_DEFAULT')

def register():
    global _room_draw_handle 
    _room_draw_handle = bpy.types.SpaceImageEditor.draw_handler_add(draw_rooms, (), 'WINDOW', 'POST_VIEW')
    bpy.app.handlers.load_post.append(_on_blendfile_load)
    

def unregister():
    if _room_draw_handle:
        bpy.types.SpaceImageEditor.draw_handler_remove(_room_draw_handle, 'WINDOW')
    bpy.app.handlers.load_post.remove(_on_blendfile_load)
    