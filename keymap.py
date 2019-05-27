import bpy


addon_keymaps = []
def register():
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name="Image", space_type='IMAGE_EDITOR', region_type='WINDOW')
    kmi = km.keymap_items.new(
        'smithy2d.scale_room',
        value='PRESS',
        type='S',
        ctrl=False,
        alt=False,
        shift=False,
        oskey=False)

    kmi = km.keymap_items.new(
        'smithy2d.grab_room',
        value='PRESS',
        type='G',
        ctrl=False,
        alt=False,
        shift=False,
        oskey=False)
    addon_keymaps.append(km)

    km = wm.keyconfigs.addon.keymaps.new(name="Window", space_type='EMPTY')
    kmi = km.keymap_items.new(
        'smithy2d.set_texture_from_file_browser',
        value='PRESS',
        type='V',
        ctrl=False,
        alt=False,
        shift=False,
        oskey=False)

    kmi = km.keymap_items.new(
        'smithy2d.export_scene_states',
        value='PRESS',
        type='F4',
        ctrl=False,
        alt=False,
        shift=False,
        oskey=False)
    addon_keymaps.append(km)

    km = wm.keyconfigs.addon.keymaps.new(name="3D View", space_type='VIEW_3D')
    kmi = km.keymap_items.new(
        'smithy2d.set_parent',
        value='PRESS',
        type='P',
        ctrl=False,
        alt=False,
        shift=False,
        oskey=False)
    addon_keymaps.append(km)


def unregister():
    wm = bpy.context.window_manager
    for km in addon_keymaps:
        for kmi in km.keymap_items:
            km.keymap_items.remove(kmi)
        wm.keyconfigs.addon.keymaps.remove(km)
    addon_keymaps.clear()