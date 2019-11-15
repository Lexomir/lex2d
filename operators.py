import bpy
import os
import uuid
import uuid
import shutil
import bmesh
import subprocess
import traceback
import mathutils
from .utils import *
from . import ObjUtils


class SetTextureFromFileBrowser(bpy.types.Operator):
    bl_idname = 'smithy2d.set_texture_from_file_browser'
    bl_label = "Smithy2D: Set Texture From File Browser"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        if not bpy.data.filepath:
            self.report({'ERROR'}, "Save the project first. This operation needs a project folder.")
            return {"CANCELLED"}

        # find open file browser window
        file_browsers = [area.spaces.active for area in context.screen.areas if area.type == 'FILE_BROWSER']
        if file_browsers:
            active_browser = file_browsers[0]
            
            # get selected file
            if bpy.app.version >= (2, 82, 0):
                abs_dirpath = active_browser.params.directory.decode()
            else:
                abs_dirpath = active_browser.params.directory
                
            abs_filepath = os.path.normpath(abs_dirpath + active_browser.params.filename)
            abs_img_dir = os.path.normpath(bpy.path.abspath(get_image_dir()))
            in_img_dir = os.path.commonpath([abs_filepath, abs_img_dir]) == abs_img_dir

            if in_img_dir:
                rel_filepath = os.path.relpath(abs_filepath, start=abs_img_dir)
            else:
                # copy the file into the img folder
                shutil.copy2(abs_filepath, abs_img_dir) # complete target filename given
                rel_filepath = os.path.basename(abs_filepath)

            # if image, set texture of active object
            filename, file_ext = os.path.splitext(abs_filepath)
            
            active_obj = context.object 
            if not active_obj or not active_obj.select_get():
                obj_name = os.path.basename(filename)
                data = bpy.data.meshes.new(obj_name)
                active_obj = bpy.data.objects.new(obj_name, data)
                move_onstage(active_obj)
                active_obj.location = bpy.context.scene.cursor.location

            if file_ext.lower() in ['.jpg', '.png']:
                spritesheet_data = find_spritesheet_data_for_image(rel_filepath)
                tile_size = spritesheet_data['tile_size'] if spritesheet_data else None

                material, tex_node = set_material_image_texture(active_obj, abs_filepath, tile_size=tile_size)
                image = tex_node.image
                tile_size = tile_size or image.size

                render_component = active_obj.smithy2d.add_component("Render2D", is_global=True)
                render_component.set_input("asset", os.path.splitext(rel_filepath)[0].replace('\\', '/'))

                # resize the plane
                cur_aspect_ratio = active_obj.scale.x / active_obj.scale.y
                aspect_ratio = tile_size[0] / tile_size[1]

                # Regenerate mesh data
                bm = create_rectangle_bmesh(screen_to_bl_size(tile_size))
                apply_bmesh_to_object(active_obj, bm)
                bm.free()

        return {'FINISHED'}

def create_rectangle(objname, location, size):
    points, faces, uvs = rectangle_mesh_data(size)

    mesh = bpy.data.meshes.new(objname)
    obj = bpy.data.objects.new(objname, mesh)

    bpy.context.scene.collection.objects.link(obj)

    # Generate mesh data
    mesh.from_pydata(points, [], faces)
    # Calculate the edges
    mesh.update(calc_edges=True)

    obj.location = location
    return obj

class Smithy2D_AddSprite(bpy.types.Operator):

    """Add Smithy2D Sprite"""
    bl_idname = "mesh.smithy2d_sprite_add"
    bl_label = "Add Smithy2D Sprite"
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    def execute(self, context):
        cursor_loc = bpy.context.scene.cursor.location
        sprite = create_rectangle("Sprite", cursor_loc, (1, 1))

        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = sprite
        sprite.select_set(state=True)
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)

class Smithy2D_EditSelectedRoomScript(bpy.types.Operator):
    bl_idname = 'smithy2d.edit_selected_room_script'
    bl_label = "Smithy2D Edit Selected Room Script"

    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):
        if not bpy.data.filepath:
            self.report({"ERROR"}, "Save the project first. This operation needs a project folder.")
            return {"CANCELLED"}
        
        scene = bpy.context.scene.smithy2d.get_active_scene()
        room = scene.get_active_room()
        if not room:
            self.report({"ERROR"}, "Create a room first. This operation needs a room folder.")
            return {"CANCELLED"}
        
        # get state name, find lua file
        variant = room.get_active_variant()
        if not room_script_exists(scene.name, room.name, variant.name):
            create_room_script(scene.name, room.name, variant.name)

        script_filepath = asset_abspath(room_script_assetpath(scene.name, room.name, variant.name))
        subprocess.run(['code', os.path.dirname(script_filepath), script_filepath], shell=True)

        return {"FINISHED"}

class Smithy2D_SetParent(bpy.types.Operator):
    bl_idname = 'smithy2d.set_parent'
    bl_label = "Smithy2D Set Parent (no inverse transform)"

    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 1 and context.active_object

    def execute(self, context):
        for o in context.selected_objects:
            if o != context.active_object:
                matrix_world = o.matrix_world
                o.parent = context.active_object
                o.matrix_parent_inverse = mathutils.Matrix()
                o.matrix_world = matrix_world 
        return {"FINISHED"}
    
class Smithy2D_SetOriginToObjectTopLeft(bpy.types.Operator):
    bl_idname = 'smithy2d.set_origin_to_obj_topleft'
    bl_label = "Smithy2D Set Origin to obj top left"

    def execute(self, context):
        bounds = ObjUtils.BoundingBox(context.object)
        scaled_bbl = [v * ov for v, ov in zip(bounds.get_bottombackleft(), context.object.scale)]
        ObjUtils.set_origin(context.object, context.object.location + mathutils.Vector(scaled_bbl))
        return {'FINISHED'}

class Smithy2D_OpenInExplorer(bpy.types.Operator):
    bl_idname = 'smithy2d.show_path_in_explorer'
    bl_label = "Smithy2D Open in Explorer"

    def execute(self, context):
        if self.path:
            the_path = self.path.replace("/", "\\")
            if os.path.exists(the_path):
                subprocess.Popen('explorer /select,"{}"'.format(the_path))
            else:
                the_path = os.path.dirname(the_path) + "\\"
                subprocess.Popen('explorer "{}"'.format(the_path))
        return {"FINISHED"}

    path : bpy.props.StringProperty()

class Smithy2D_VariantAddOperator(bpy.types.Operator):
    bl_idname = "smithy2d.variant_adder"
    bl_label = "Add Variant"
    bl_property = "variant_name"
    bl_options = {"REGISTER"}

    def draw(self, context):
        layout = self.layout
        if self.warning:
            layout.label(text=self.warning)
        layout.prop(self, "variant_name", text="Name")

    def execute(self, context):
        self.warning = ""
        scene = context.scene.smithy2d.get_active_scene()
        room = scene.get_active_room() if scene else None
        if not room:
            self.report({"ERROR"}, "Can't create variant. No room is active.")
            return {"CANCELLED"}

        variant_assetpath = room_script_assetpath(scene.name, room.name, self.variant_name)
        if not self.variant_name:
            self.warning = "Please type something"
            return context.window_manager.invoke_props_dialog(self)
        elif os.path.exists(asset_abspath(variant_assetpath)):
            self.warning = "There is already a variant file with that name" 
            return context.window_manager.invoke_props_dialog(self)
        else:
            variant = room.variants.add()
            variant.init(self.variant_name)
            variant_guid = "{}\t{}\n".format(variant.guid, variant_assetpath)

            # add guids to guid file
            guid_filepath = get_guid_mapfile()
            with open(guid_filepath, "a") as guid_file:
                guid_file.write(variant_guid)

            if variant and self.duplicate:
                variant.save_scene_state(bpy.context.scene)

            room.set_variant_and_update(len(room.variants) - 1)
            refresh_screen_area(context.area.type)
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def update_name(self, context):
        scene = context.scene.smithy2d.get_active_scene()
        room = scene.get_active_room()
        variant_assetpath = room_script_assetpath(scene.name, room.name, self.variant_name)
        if not valid_variant_assetpath(variant_assetpath):
            self.warning = "Invalid variant name"
        elif os.path.exists(asset_abspath(variant_assetpath)):
            self.warning = "There is already a variant file with that name" 
        return 

    duplicate : bpy.props.BoolProperty(default=False)
    warning : bpy.props.StringProperty()
    variant_name : bpy.props.StringProperty(update=update_name)

class Smithy2D_RoomAddOperator(bpy.types.Operator):
    bl_idname = "smithy2d.room_adder"
    bl_label = "Add Room"
    bl_property = "room_name"
    bl_options = {"REGISTER"}

    def draw(self, context):
        layout = self.layout
        if self.warning:
            layout.label(text=self.warning)
        layout.prop(self, "room_name", text="Name")

    def execute(self, context):
        self.warning = ""
        scene = context.scene.smithy2d.get_active_scene()
        if not scene:
            self.report({"ERROR"}, "Can't create room. No scene is active.")
            return {"CANCELLED"}

        room_assetpath = room_dir_assetpath(scene.name, self.room_name)
        if not self.room_name:
            self.warning = "Please type something"
            return context.window_manager.invoke_props_dialog(self)
        elif os.path.exists(asset_abspath(room_assetpath)):
            self.warning = "There is already a scene directory with that name" 
            return context.window_manager.invoke_props_dialog(self)
        else:
            room = scene.rooms.add()
            room.init(self.room_name)
            room_guids = ["{}\t{}\n".format(room.guid, room_assetpath)]
            for variant in room.variants:
                variant_assetpath = room_script_assetpath(scene.name, room.name, variant.name)
                room_guids.append("{}\t{}\n".format(variant.guid, variant_assetpath))

            # add guids to guid file
            guid_filepath = get_guid_mapfile()
            with open(guid_filepath, "a") as guid_file:
                guid_file.writelines(room_guids)

            variant = room.get_active_variant() 
            if variant and self.duplicate:
                variant.save_scene_state(bpy.context.scene)

            scene.set_room_and_update(len(scene.rooms) - 1)
            refresh_screen_area(context.area.type)
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def update_name(self, context):
        context.scene.smithy2d.get_active_scene()
        room_assetpath = room_dir_assetpath(scene.name, self.room_name)
        if not valid_room_assetpath(room_assetpath):
            self.warning = "Invalid room name"
        elif os.path.exists(asset_abspath(room_assetpath)):
            self.warning = "There is already a room directory with that name" 
        return 

    duplicate : bpy.props.BoolProperty(default=False)
    warning : bpy.props.StringProperty()
    room_name : bpy.props.StringProperty(update=update_name)

class Smithy2D_SceneAddOperator(bpy.types.Operator):
    bl_idname = "smithy2d.scene_adder"
    bl_label = "Add Scene"
    bl_property = "scene_name"
    bl_options = {"REGISTER"}

    def draw(self, context):
        layout = self.layout
        if self.warning:
            layout.label(text=self.warning)
        layout.prop(self, "scene_name", text="Name")

    def execute(self, context):
        self.warning = ""
        scene_assetpath = scene_dir_assetpath(self.scene_name)
        if not self.scene_name:
            self.warning = "Please type something"
            return context.window_manager.invoke_props_dialog(self)
        elif os.path.exists(asset_abspath(scene_assetpath)):
            self.warning = "There is already a scene directory with that name" 
            return context.window_manager.invoke_props_dialog(self)
        else:
            scene = context.scene.smithy2d.scenes.add()
            scene.init(self.scene_name)
            scene_guids = ["{}\t{}\n".format(scene.guid, scene_assetpath)]
            for room in scene.rooms:
                room_assetpath = room_dir_assetpath(scene.name, room.name)
                scene_guids.append("{}\t{}\n".format(room.guid, room_assetpath))
                for variant in room.variants:
                    variant_assetpath = room_script_assetpath(scene.name, room.name, variant.name)
                    scene_guids.append("{}\t{}\n".format(variant.guid, variant_assetpath))

            # add guids to guid file
            guid_filepath = get_guid_mapfile()
            with open(guid_filepath, "a") as guid_file:
                guid_file.writelines(scene_guids)

            room = scene.get_active_room() 
            variant = room.get_active_variant() if room else None
            if variant and self.duplicate:
                variant.save_scene_state(bpy.context.scene)

            context.scene.smithy2d.set_scene_and_update(len(context.scene.smithy2d.scenes) - 1)
            refresh_screen_area(context.area.type)
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def update_name(self, context):
        scene_assetpath = scene_dir_assetpath(self.scene_name)
        if not valid_scene_assetpath(scene_assetpath):
            self.warning = "Invalid scene name"
        elif os.path.exists(asset_abspath(scene_assetpath)):
            self.warning = "There is already a scene directory with that name" 
        return 

    duplicate : bpy.props.BoolProperty(default=False)
    warning : bpy.props.StringProperty()
    scene_name : bpy.props.StringProperty(update=update_name)

def rename_room_directory(scene_name, old_name, name):
    try:
        print("Renaming room directory '{}' to '{}'".format(old_name, name))
        old_room_dir_assetpath = room_dir_assetpath(scene_name, old_name)
        old_room_dir_abspath = asset_abspath(old_room_dir_assetpath)
        new_room_dir_assetpath = room_dir_assetpath(scene_name, name)
        new_room_dir_abspath = asset_abspath(new_room_dir_assetpath)
        if os.path.exists(old_room_dir_abspath):
            os.rename(old_room_dir_abspath, new_room_dir_abspath)
        else:
            print("Smithy2D - Warning: Renaming a room but the original directory could not be found ('{}')".format(old_room_dir_abspath))
            os.makedirs(new_room_dir_abspath)
        
        # rename the room and its assets in the guid file
        guid_map_filepath = get_guid_mapfile()
        tmp_guid_map_filepath = guid_map_filepath + ".tmp"
        with open(guid_map_filepath, "r") as guid_file:
            with open(tmp_guid_map_filepath, "w") as tmp_guid_file:
                for line in guid_file:
                    line_assetpath = line.split('\t')[1].rstrip()
                    if line_assetpath.startswith(old_room_dir_assetpath):
                        line = line.replace(old_room_dir_assetpath, new_room_dir_assetpath, 1)
                    tmp_guid_file.write(line)
        os.replace(tmp_guid_map_filepath, guid_map_filepath)
        return True
    except Exception as e:
        traceback.print_exc()
        return False

def rename_variant_script(scene_name, room_name, old_variant_name, new_variant_name):
    try:
        print("Renaming variant script '{}' to '{}'".format(old_variant_name, new_variant_name))
        # rename variant script file
        old_script_assetpath = room_script_assetpath(scene_name, room_name, old_variant_name)
        old_script_filepath = asset_abspath(old_script_assetpath)
        new_script_assetpath = room_script_assetpath(scene_name, room_name, new_variant_name)
        new_script_filepath = asset_abspath(new_script_assetpath)
        if os.path.exists(old_script_filepath):
            os.rename(old_script_filepath, new_script_filepath)
        else:
            print("Smithy2D - Warning: Renaming a Variant but the original script could not be found ('{}')".format(old_script_filepath))

        # rename the variant
        guid_map_filepath = get_guid_mapfile()
        tmp_guid_map_filepath = guid_map_filepath + ".tmp"
        with open(guid_map_filepath, "r") as guid_file:
            with open(tmp_guid_map_filepath, "w") as tmp_guid_file:
                for line in guid_file:
                    line_assetpath = line.split('\t')[1].rstrip()
                    if line_assetpath.startswith(old_script_assetpath):
                        line = line.replace(old_script_assetpath, new_script_assetpath, 1)
                    tmp_guid_file.write(line)
        os.replace(tmp_guid_map_filepath, guid_map_filepath)
        return True
    except:
        return False

def rename_scene(old_scene_name, new_scene_name):
    try:
        print("Renaming Scene directory '{}' to '{}'".format(old_scene_name, new_scene_name))
        # rename variant script file
        old_scene_dir_assetpath = scene_dir_assetpath(old_scene_name)
        old_scene_dir_abspath = asset_abspath(old_scene_dir_assetpath)
        new_scene_assetpath = scene_dir_assetpath(new_scene_name)
        new_scene_abspath = asset_abspath(new_scene_assetpath)
        if os.path.exists(old_scene_dir_abspath):
            os.rename(old_scene_dir_abspath, new_scene_abspath)
        else:
            print("Smithy2D - Warning: Renaming a Scene but the original directory could not be found ('{}')".format(old_scene_dir_abspath))
        
        # rename the scene and its assets in the guid file
        guid_map_filepath = get_guid_mapfile()
        tmp_guid_map_filepath = guid_map_filepath + ".tmp"
        with open(guid_map_filepath, "r") as guid_file:
            with open(tmp_guid_map_filepath, "w") as tmp_guid_file:
                for line in guid_file:
                    line_assetpath = line.split('\t')[1].rstrip()
                    if line_assetpath.startswith(old_scene_dir_assetpath):
                        line = line.replace(old_scene_dir_assetpath, new_scene_assetpath, 1)
                    tmp_guid_file.write(line)
        os.replace(tmp_guid_map_filepath, guid_map_filepath)
        return True
    except:
        return False

class VariantRenameOperator(bpy.types.Operator):
    bl_idname = "smithy2d.variant_renamer"
    bl_label = "Rename Variant"
    bl_options = {'REGISTER', 'UNDO'}
    bl_property = "name"

    def draw(self, context):
        if not self.is_valid:
            row = self.layout.row()
            variant = context.scene.path_resolve(self.variant_datapath)
            room = variant.get_room()
            scene = room.get_scene()
            script_assetpath = room_script_assetpath(scene.name, room.name, self.name)
            script_filepath = asset_abspath(script_assetpath)
            row.label(text=self.warning)
            operator = row.operator('smithy2d.show_path_in_explorer', icon="FILEBROWSER", text="")
            operator.path = script_filepath.replace('/', '\\')
        self.layout.prop(self, "name", text="Name")

    def execute(self, context):
        if not self.variant_datapath:
            self.report({"ERROR"}, "No room datapath? name: '{}'".format(self.name))
            return {"FINISHED"}
        
        variant = context.scene.path_resolve(self.variant_datapath)
       
        # validate the name
        if not self.name:
            self.is_valid = False
            self.warning = "Please type something"
        elif self.name == variant.name:
            return {"FINISHED"}
        else:
            self.validate_name(context)

        # try to rename
        if self.is_valid:
            room = variant.get_room()
            scene = room.get_scene()
            self.is_valid = rename_variant_script(scene.name, room.name, variant.name, self.name)
            if self.is_valid:
                variant.set_name(self.name)
                refresh_screen_area(context.area.type)
            else:
                self.warning = "Can't rename variant. An external process is using the variant script"
                return context.window_manager.invoke_props_dialog(self, width=360)
        else:
            return context.window_manager.invoke_props_dialog(self, width=360)
        return {"FINISHED"}

    def invoke(self, context, event):
        sd = self.variant_datapath
        if not sd:
            print("OUCH")
        return context.window_manager.invoke_props_dialog(self)
    
    def check_name_exists(self, context):
        variant = context.scene.path_resolve(self.variant_datapath)
        room = variant.get_room()
        scene = room.get_scene()
        script_assetpath = room_script_assetpath(scene.name, room.name, self.name)
        script_filepath = asset_abspath(script_assetpath)
        return os.path.exists(script_filepath)

    def validate_name(self, context):
        variant = context.scene.path_resolve(self.variant_datapath)
        if self.name and self.name != variant.name:
            self.is_valid = not VariantRenameOperator.check_name_exists(self, context)
            self.warning = "There is already a variant script with that name" 

    name : bpy.props.StringProperty(update=validate_name, options={'TEXTEDIT_UPDATE'})
    warning : bpy.props.StringProperty()
    is_valid : bpy.props.BoolProperty(default=True)
    variant_datapath : bpy.props.StringProperty() # data path from the underlying id_data

class RoomRenameOperator(bpy.types.Operator):
    bl_idname = "smithy2d.room_renamer"
    bl_label = "Rename Room"
    bl_options = {'REGISTER', 'UNDO'}
    bl_property = "name"

    def draw(self, context):
        if not self.is_valid:
            row = self.layout.row()
            room = context.scene.path_resolve(self.room_datapath)
            scene = room.get_scene()
            room_assetpath = room_dir_assetpath(scene.name, self.name)
            room_abspath = asset_abspath(room_assetpath)
            row.label(text=self.warning)
            operator = row.operator('smithy2d.show_path_in_explorer', icon="FILEBROWSER", text="")
            operator.path = room_abspath.replace('/', '\\')
        self.layout.prop(self, "name", text="Name")

    def execute(self, context):
        if not self.room_datapath:
            self.report({"ERROR"}, "No room datapath? name: '{}'".format(self.name))
            return {"FINISHED"}
        
        room = context.scene.path_resolve(self.room_datapath)
        
        # validate the name
        if not self.name:
            self.is_valid = False
            self.warning = "Please type something"
        elif self.name == room.name:
            return {"FINISHED"}
        else:
            self.validate_name(context)
        
        # try to rename
        if self.is_valid:
            scene = room.get_scene()
            self.is_valid = rename_room_directory(scene.name, room.name, self.name)
            if self.is_valid:
                room.set_name(self.name)
                refresh_screen_area(context.area.type)
            else:
                self.warning = "Can't rename room. An external process is using the directory"
                return context.window_manager.invoke_props_dialog(self, width=360)
        else:
            return context.window_manager.invoke_props_dialog(self, width=360)
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def check_name_exists(self, context):
        room = context.scene.path_resolve(self.room_datapath)
        scene = room.get_scene()
        old_room_dir_assetpath = room_dir_assetpath(scene.name, room.name)
        old_room_dir_abspath = asset_abspath(old_room_dir_assetpath)
        new_room_dir_assetpath = room_dir_assetpath(scene.name, self.name)
        new_room_dir_abspath = asset_abspath(new_room_dir_assetpath)
        return os.path.exists(new_room_dir_abspath)

    def validate_name(self, context):
        room = context.scene.path_resolve(self.room_datapath)
        if self.name and self.name != room.name:
            self.is_valid = not RoomRenameOperator.check_name_exists(self, context)
            self.warning = "There is already a room directory with that name" 

    name : bpy.props.StringProperty(update=validate_name, options={'TEXTEDIT_UPDATE'})
    warning : bpy.props.StringProperty()
    is_valid : bpy.props.BoolProperty(default=True)
    room_datapath : bpy.props.StringProperty() # data path from the underlying id_data

class SceneRenameOperator(bpy.types.Operator):
    bl_idname = "smithy2d.scene_renamer"
    bl_label = "Rename Scene"
    bl_options = {'REGISTER', 'UNDO'}
    bl_property = "name"

    def draw(self, context):
        if not self.is_valid:
            row = self.layout.row()
            scene = context.scene.path_resolve(self.scene_datapath)
            scene_assetpath = scene_dir_assetpath(self.name)
            scene_abspath = asset_abspath(scene_assetpath)
            row.label(text=self.warning)
            operator = row.operator('smithy2d.show_path_in_explorer', icon="FILEBROWSER", text="")
            operator.path = scene_abspath.replace('/', '\\')
        self.layout.prop(self, "name", text="Name")

    def execute(self, context):
        if not self.scene_datapath:
            self.report({"ERROR"}, "No scene datapath? name: '{}'".format(self.name))
            return {"FINISHED"}

        scene = context.scene.path_resolve(self.scene_datapath)
        if not self.name:
            self.is_valid = False
            self.warning = "Please type something"
        elif self.name == scene.name:
            return {"FINISHED"}
        else:
            self.validate_name(context)

        if self.is_valid:
            scene = context.scene.path_resolve(self.scene_datapath)
            self.is_valid = rename_scene(scene.name, self.name)
            if self.is_valid:
                scene.set_name(self.name)
                refresh_screen_area(context.area.type)
            else:
                self.warning = "An external process is using the scene directory"
                return context.window_manager.invoke_props_dialog(self, width=360)
        else:
            return context.window_manager.invoke_props_dialog(self, width=360)
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def check_name_exists(self, context):
        scene = context.scene.path_resolve(self.scene_datapath)
        new_scene_assetpath = scene_dir_assetpath(self.name)
        new_scene_abspath = asset_abspath(new_scene_assetpath)
        return os.path.exists(new_scene_abspath)

    def validate_name(self, context):
        scene = context.scene.path_resolve(self.scene_datapath)
        if self.name and self.name != scene.name:
            self.is_valid = not SceneRenameOperator.check_name_exists(self, context)
            self.warning = "There is already a scene directory with that name" 

    name : bpy.props.StringProperty(update=validate_name, options={'TEXTEDIT_UPDATE'})
    warning : bpy.props.StringProperty()
    is_valid : bpy.props.BoolProperty(default=True)
    scene_datapath : bpy.props.StringProperty() # data path from the underlying id_data

class VariantDeleterOperator(bpy.types.Operator):
    bl_idname = "smithy2d.variant_deleter"
    bl_label = "Delete Room"
    bl_options = {'REGISTER', 'UNDO'}

    def draw(self, context):
        if self.warning:
            self.layout.label(text=self.warning)
            self.layout.separator()
        col = self.layout.column(align = True)
        col.label(text="Are you sure you want to delete this Variant?")
        col.separator()

    def execute(self, context):
        if not self.datapath:
            self.report({"ERROR"}, "No variant datapath?")
            return {"FINISHED"}
        
        variant = context.scene.path_resolve(self.datapath)
        room = variant.get_room()
        scene = room.get_scene()
        variant_assetpath = room_script_assetpath(scene.name, room.name, variant.name)
        variant_guid = variant.guid
        self.warning = ""
        asset_exists = True
        if not valid_variant_assetpath(variant_assetpath):
            asset_exists = False

        print("Deleting variant '{}'".format(variant))
        try:
            # delete from disk
            if asset_exists:
                archive_and_delete_asset(variant_assetpath)
            # delete from ui
            collection = room.variants
            idx = find_item_idx(collection, variant)
            active_idx = room.active_variant_index
            if idx != -1:
                # remove the original list entry
                new_active_idx = idx
                if idx == active_idx and (idx != 0 or len(collection) == 1):
                    new_active_idx -= 1
                collection.remove(idx)
                
                # log
                if collection and new_active_idx >= 0:
                    new_variant = collection[new_active_idx]
                    print("Switching to variant '{}'".format(new_variant))

                # highlight and load the next scene
                room.set_variant(new_active_idx)
                room.load_variant(new_active_idx, force=True)
            
            # remove from guids mapfile
            guid_map_filepath = get_guid_mapfile()
            tmp_guid_map_filepath = guid_map_filepath + ".tmp"
            if os.path.exists(guid_map_filepath):
                with open(guid_map_filepath, "r") as guid_file:
                    with open(tmp_guid_map_filepath, "w") as tmp_guid_file:
                        for line in guid_file:
                            if line.split('\t')[0] != variant_guid:
                                tmp_guid_file.write(line)
                os.replace(tmp_guid_map_filepath, guid_map_filepath)

            refresh_screen_area(context.area.type)
        except OSError as e:
            self.warning = "Can't delete the Variant. It's being used by an external process"
            return context.window_manager.invoke_props_dialog(self, width=360)
        except InvalidDeleteException as e:
            traceback.print_exc()
            self.report({"ERROR"}, "TRIED TO DELETE CORE, check the log")
        except Exception as e:
            traceback.print_exc()
            self.report({"ERROR"}, "Something went wrong, check the log")
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    datapath : bpy.props.StringProperty()
    warning : bpy.props.StringProperty()

class RoomDeleterOperator(bpy.types.Operator):
    bl_idname = "smithy2d.room_deleter"
    bl_label = "Delete Room"
    bl_options = {'REGISTER', 'UNDO'}

    def draw(self, context):
        if self.warning:
            self.layout.label(text=self.warning)
            self.layout.separator()

        col = self.layout.column(align = True)
        #col.alignment = 'EXPAND'
        if not self.warning:
            col.label(text="Are you sure you want to delete this Room?")
            col.label(text="(along with all of its variants and components)")
        else:
            col.label(text="Try again?")
        col.separator()

    def execute(self, context):
        if not self.datapath:
            self.report({"ERROR"}, "No room datapath?")
            return {"FINISHED"}

        room = context.scene.path_resolve(self.datapath)
        scene = room.get_scene()
        room_assetpath = room_dir_assetpath(scene.name, room.name)

        # collect the rooms guids (to remove them from the guids file later)
        room_guids = [room.guid]
        for variant in room.variants:
            room_guids.append(variant.guid)

        self.warning = ""
        asset_exists = True
        if not valid_room_assetpath(room_assetpath):
            asset_exists = False

        print("Deleting room '{}'".format(room))
        try:
            # delete from disk
            if asset_exists:
                archive_and_delete_asset(room_assetpath)

            # delete from ui
            collection = scene.rooms
            idx = find_item_idx(collection, room)
            active_idx = scene.active_room_index
            if idx != -1:
                # remove the original list entry
                new_active_idx = idx
                if idx == active_idx and (idx != 0 or len(collection) == 1):
                    new_active_idx -= 1
                collection.remove(idx)
                
                # log
                if collection and new_active_idx >= 0:
                    new_room = collection[new_active_idx]
                    print("Switching to room '{}'".format(new_room))

                # highlight and load the next scene
                scene.set_room(new_active_idx)
                scene.load_room(new_active_idx, force=True)

            # remove from guids mapfile
            guid_map_filepath = get_guid_mapfile()
            tmp_guid_map_filepath = guid_map_filepath + ".tmp"
            if os.path.exists(guid_map_filepath):
                with open(guid_map_filepath, "r") as guid_file:
                    with open(tmp_guid_map_filepath, "w") as tmp_guid_file:
                        for line in guid_file:
                            if line.split('\t')[0] not in room_guids:
                                tmp_guid_file.write(line)
                os.replace(tmp_guid_map_filepath, guid_map_filepath)                

            refresh_screen_area(context.area.type)
        except OSError as e:
            self.warning = "Can't delete the Room. It's being used by an external process"
            return context.window_manager.invoke_props_dialog(self, width=360)
        except InvalidDeleteException as e:
            traceback.print_exc()
            self.report({"ERROR"}, "TRIED TO DELETE CORE, check the log")
        except Exception as e:
            traceback.print_exc()
            self.report({"ERROR"}, "Something went wrong, check the log")
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    datapath : bpy.props.StringProperty()
    warning : bpy.props.StringProperty()

class SceneDeleterOperator(bpy.types.Operator):
    bl_idname = "smithy2d.scene_deleter"
    bl_label = "Delete Scene"
    bl_options = {'REGISTER', 'UNDO'}

    def draw(self, context):
        if self.warning:
            self.layout.label(text=self.warning)
            self.layout.separator()
        col = self.layout.column(align = True)
        col.label(text="Are you sure you want to delete this scene?")
        col.label(text="(along with all of its rooms, variants, and components)")
        col.separator()

    def execute(self, context):
        if not self.datapath:
            self.report({"ERROR"}, "No scene datapath?")
            return {"FINISHED"}

        smithy_scene = context.scene.path_resolve(self.datapath)
        scene_assetpath = scene_dir_assetpath(smithy_scene.name)

        # collect all scene guids (to remove them from the guid file later)
        scene_guids = [smithy_scene.guid]
        for room in smithy_scene.rooms:
            scene_guids.append(room.guid)
            for variant in room.variants:
                scene_guids.append(variant.guid)

        self.warning = ""
        asset_exists = True
        if not valid_scene_assetpath(scene_assetpath):
            asset_exists = False

        print("Deleting scene '{}'".format(smithy_scene))
        try:
            # delete from disk
            if asset_exists:
                archive_and_delete_asset(scene_assetpath)

            # delete from ui
            collection = context.scene.smithy2d.scenes
            idx = find_item_idx(collection, smithy_scene)
            active_idx = context.scene.smithy2d.active_scene_index
            if idx != -1:
                # remove the list entry
                new_active_idx = idx
                if idx == active_idx and (idx != 0 or len(collection) == 1):
                    new_active_idx -= 1
                collection.remove(idx)

                # log
                if collection and new_active_idx >= 0:
                    new_scene = collection[new_active_idx]
                    print("Switching to scene '{}'".format(new_scene))

                # highlight the previous scene and load its contents
                context.scene.smithy2d.set_scene(new_active_idx)
                context.scene.smithy2d.load_scene(new_active_idx, force=True)
            
            # remove from guids mapfile
            guid_map_filepath = get_guid_mapfile()
            tmp_guid_map_filepath = guid_map_filepath + ".tmp"
            if os.path.exists(guid_map_filepath):
                with open(guid_map_filepath, "r") as guid_file:
                    with open(tmp_guid_map_filepath, "w") as tmp_guid_file:
                        for line in guid_file:
                            if line.split('\t')[0] not in scene_guids:
                                tmp_guid_file.write(line)
                os.replace(tmp_guid_map_filepath, guid_map_filepath)

            refresh_screen_area(context.area.type)
        except OSError as e:
            self.warning = "Can't delete the scene. It's being used by an external process"
            return context.window_manager.invoke_props_dialog(self, width=360)
        except InvalidDeleteException as e:
            traceback.print_exc()
            self.report({"ERROR"}, "TRIED TO DELETE CORE, check the log")
        except Exception as e:
            traceback.print_exc()
            self.report({"ERROR"}, "Something went wrong, check the log")
        return {"FINISHED"}

    def invoke(self, context, event):
        self.force = event.shift
        return context.window_manager.invoke_props_dialog(self)

    datapath : bpy.props.StringProperty()
    warning : bpy.props.StringProperty()

class SyncWithAssetFolder(bpy.types.Operator):
    bl_idname = "smithy2d.sync_with_asset_folder"
    bl_label = "Sync With Asset Folder"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return bpy.data.filepath

    def execute(self, context):
        def create_guid():
            return str(uuid.uuid4())

        # sync existing assets with contents on disk
        guid_map = {}
        assetpath_map = {}
        guid_map_filepath = get_guid_mapfile()
        os.makedirs(os.path.dirname(guid_map_filepath), exist_ok=True)
        file_access = "r+" if os.path.exists(guid_map_filepath) else "w+"
        with open(guid_map_filepath, file_access) as guid_file:
            # parse the guids from the guid-assetpath map file
            for line in guid_file:
                line_parts = line.split("\t")
                guid, assetpath = line_parts[0], line_parts[1].rstrip()
                guid_map[guid] = assetpath
                assetpath_map[guid] = guid
            
            # rename each scene according to its mapped directories
            for scene in context.scene.smithy2d.scenes:
                current_assetpath = scene_dir_assetpath(scene.name)
                if not scene.guid:
                    if current_assetpath in assetpath_map:
                        self.report({"ERROR"}, "This scene doesn't have a guid, but somehow its directory is in the guid mapfile.")
                    scene.guid = create_guid()

                # if no guid, this scene gets linked to the directory of its current name
                new_assetpath = guid_map.get(scene.guid)
                if not new_assetpath:
                    new_assetpath = current_assetpath
                    guid_file.write("{}\t{}\n".format(scene.guid, new_assetpath))
                    guid_map[scene.guid] = new_assetpath
                # set the scene's name according to its directory name
                scene.name = scene_from_assetpath(new_assetpath)

                # rename each room according to its mapped directories
                for room in scene.rooms:
                    current_assetpath = room_dir_assetpath(scene.name, room.name)
                    if not room.guid:
                        if current_assetpath in assetpath_map:
                            self.report({"ERROR"}, "This room doesn't have a guid, but somehow its directory is in the guid mapfile.")
                        room.guid = create_guid()

                    # if no guid, this room gets linked to the directory of its current name
                    new_assetpath = guid_map.get(room.guid)
                    if not new_assetpath:
                        new_assetpath = current_assetpath
                        guid_file.write("{}\t{}\n".format(room.guid, new_assetpath))
                        guid_map[room.guid] = new_assetpath
                    # set the room's name according to its directory name
                    room.name = room_from_assetpath(new_assetpath)

                    # rename each variant according to its mapped script file
                    for variant in room.variants:
                        current_assetpath = room_script_assetpath(scene.name, room.name, variant.name)
                        if not variant.guid:
                            if current_assetpath in assetpath_map:
                                self.report({"ERROR"}, "This variant doesn't have a guid, but somehow its script is in the guid mapfile.")
                            variant.guid = create_guid()

                        # if no guid, this variant gets linked to the file of its current name
                        new_assetpath = guid_map.get(variant.guid)
                        if not new_assetpath:
                            new_assetpath = current_assetpath
                            guid_file.write("{}\t{}\n".format(variant.guid, new_assetpath))
                            guid_map[variant.guid] = new_assetpath
                        # set the variant's name according to its script name
                        variant.name = variant_from_assetpath(new_assetpath)

            # find new assets on disk
            scenes_dir = asset_abspath("scripts/")
            for scene_name in os.listdir(scenes_dir):
                if scene_name != "core" and os.path.isdir(os.path.join(scenes_dir, scene_name)):
                    scene = context.scene.smithy2d.scenes.get(scene_name)
                    scene_assetpath = scene_dir_assetpath(scene_name)
                    scene_abspath = asset_abspath(scene_assetpath)
                    # add scene if it doesnt exist in the blendfile
                    if not scene:
                        scene = context.scene.smithy2d.scenes.add()
                        scene.name = scene_name
                        scene.guid = assetpath_map.get(scene_assetpath) or ""
                        if not scene.guid:
                            scene.guid = create_guid()
                            guid_file.write("{}\t{}\n".format(scene.guid, scene_assetpath))

                    # find new room assets on disk
                    for room_name in os.listdir(scene_abspath):
                        if os.path.isdir(os.path.join(scene_abspath, room_name)):
                            room = scene.rooms.get(room_name)
                            room_assetpath = room_dir_assetpath(scene_name, room_name)
                            room_abspath = asset_abspath(room_assetpath)
                            # add room if it doesnt exist in the blendfile
                            if not room:
                                room = scene.rooms.add()
                                room.name = room_name
                                room.guid = assetpath_map.get(room_assetpath) or ""
                                if not room.guid:
                                    room.guid = create_guid()
                                    guid_file.write("{}\t{}\n".format(room.guid, room_assetpath))

                            # find new variant assets on disk
                            variants_dir = os.path.join(room_abspath, "states")
                            if os.path.exists(variants_dir) and os.path.isdir(variants_dir):
                                for variant_filename in os.listdir(variants_dir):
                                    variant_name, ext = os.path.splitext(variant_filename)
                                    if ext == ".lua":
                                        variant = room.variants.get(variant_name)
                                        variant_assetpath = room_script_assetpath(scene_name, room_name, variant_name)
                                        # add variant if it doesnt exist in the blendfile
                                        if not variant:
                                            variant = room.variants.add()
                                            variant.name = variant_name
                                            variant.guid = assetpath_map.get(variant_assetpath) or ""
                                            if not variant.guid:
                                                variant.guid = create_guid()
                                                guid_file.write("{}\t{}\n".format(variant.guid, variant_assetpath))

        return {"FINISHED"}


def draw_item(self, context):
    self.layout.operator("mesh.smithy2d_sprite_add", icon="GHOST_ENABLED", text='Sprite')

def register():
    bpy.types.VIEW3D_MT_mesh_add.prepend(draw_item)

def unregister():
    bpy.types.VIEW3D_MT_mesh_add.remove(draw_item)
