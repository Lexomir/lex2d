import bpy
import os
import shutil
import bmesh

from .utils import *



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

                # resize the plane
                cur_aspect_ratio = active_obj.scale.x / active_obj.scale.y
                aspect_ratio = tile_size[0] / tile_size[1]

                # Regenerate mesh data
                bm = create_rectangle_bmesh(screen_to_bl_size(tile_size))
                
                mode = bpy.context.mode
                bpy.ops.object.mode_set(mode='OBJECT')
                bm.to_mesh(active_obj.data)
                bpy.ops.object.mode_set(mode=mode)
                
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

class Lex2D_AddSprite(bpy.types.Operator):

    """Add Lex2D Sprite"""
    bl_idname = "mesh.lex2d_sprite_add"
    bl_label = "Add Lex2D Sprite"
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


def draw_item(self, context):
    self.layout.operator("mesh.lex2d_sprite_add", icon="GHOST_ENABLED", text='Sprite')
        

def register():
    bpy.types.VIEW3D_MT_mesh_add.prepend(draw_item)


def unregister():
    bpy.types.VIEW3D_MT_mesh_add.remove(draw_item)
