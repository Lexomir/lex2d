import bpy
import os
import shutil

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
        active_obj = context.object 

        # find open file browser window
        file_browsers = [area.spaces.active for area in context.screen.areas if area.type == 'FILE_BROWSER']
        if file_browsers:
            active_browser = file_browsers[0]
            
            # get selected file
            abs_filepath = active_browser.params.directory + active_browser.params.filename
            abs_img_dir = bpy.path.abspath(get_image_dir())
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
