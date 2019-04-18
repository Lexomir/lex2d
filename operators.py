import bpy
import os
import shutil
import bmesh

from .utils import *



def find_spritesheet_data_for_image(image_filepath):
    # find spritesheet file
    abs_image_filepath = bpy.path.abspath(get_image_dir() + image_filepath)
    abs_image_dir = os.path.dirname(abs_image_filepath)
    abs_spritesheet_filepath = os.path.join(abs_image_dir, "definitions", "spritesheets.txt")

    rel_image_filepath = os.path.relpath(abs_image_filepath, start=bpy.path.abspath(get_asset_dir()))
    try:
        with open(abs_spritesheet_filepath, "r") as spritesheet_file:
            for line in spritesheet_file:
                line_parts = line.split(" ")
                referenced_image_rel_filepath = line_parts[2]
                if line_parts[0] == 'png_sheet' and os.path.normcase(referenced_image_rel_filepath) == os.path.normcase(rel_image_filepath):
                    try: tile_size = (int(line_parts[3]), int(line_parts[4]))
                    except: return None

                    return {"tile_size": tile_size}
    except FileNotFoundError:
        return None
    except: 
        print('Unhandled error: %s' % sys.exc_info()[0])
        return None

class SetTextureFromFileBrowser(bpy.types.Operator):
    bl_idname = 'lex2d.set_texture_from_file_browser'
    bl_label = "Lex2D Set Texture From File Browser"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        if not bpy.data.filepath:
            self.report({'ERROR'}, "Save the project first. This operation needs a project folder.")
            return {"CANCELLED"}

        active_obj = context.object 

        # find open file browser window
        file_browsers = [area.spaces.active for area in context.screen.areas if area.type == 'FILE_BROWSER']
        if file_browsers:
            active_browser = file_browsers[0]
            
            # get selected file
            abs_filepath = os.path.normpath(active_browser.params.directory + active_browser.params.filename)
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
            if file_ext.lower() in ['.jpg', '.png']:
                spritesheet_data = find_spritesheet_data_for_image(rel_filepath)
                tile_size = spritesheet_data['tile_size'] if spritesheet_data else None

                material, tex_node = set_material_image_texture(active_obj, abs_filepath, tile_size=tile_size)
                image = tex_node.image
                tile_size = tile_size or image.size

                render_component = active_obj.lexgame.smithy.add_component("Render2D")
                render_component.set_input("asset", os.path.splitext(rel_filepath)[0])
                render_component.set_input("tile_size", list(tile_size))

                # resize the plane
                cur_aspect_ratio = active_obj.scale.x / active_obj.scale.y
                aspect_ratio = tile_size[0] / tile_size[1]
                active_obj.scale.x *= aspect_ratio / cur_aspect_ratio

        return {'FINISHED'}

def create_custom_mesh(objname, px, py, pz):
        # vertices
        points = [
            (0.0, -1.0, 0.0), # BL
            (1.0, -1.0, 0.0), # BR
            (0.0, 0.0, 0.0),  # TL
            (1.0, 0.0, 0.0)]  # TR

        # faces
        faces = [(0, 1, 3, 2)]

        mesh = bpy.data.meshes.new(objname)
        obj = bpy.data.objects.new(objname, mesh)

        bpy.context.scene.collection.objects.link(obj)

        # Generate mesh data
        mesh.from_pydata(points, [], faces)
        # Calculate the edges
        mesh.update(calc_edges=True)

        obj.location = (px, py, pz)
        return obj

class Lex2D_AddSprite(bpy.types.Operator):

    """Add Lex2D Sprite"""
    bl_idname = "mesh.lex2d_sprite_add"
    bl_label = "Add Lex2D Sprite"
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    def execute(self, context):
        cursor_loc = bpy.context.scene.cursor.location
        sprite = create_custom_mesh("Sprite", *cursor_loc)

        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = sprite
        sprite.select_set(state=True)
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)


def draw_item(self, context):
    self.layout.operator("mesh.lex2d_sprite_add", icon="GHOST_ENABLED", text='Sprite')
        

def register():
    bpy.types.VIEW3D_MT_mesh_add.prepend(draw_item)


def unregister():
    bpy.types.VIEW3D_MT_mesh_add.remove(draw_item)
