import bpy
import bmesh
import mathutils

def get_bounds(obj):
    return BoundingBox(obj)

def shift_verts(obj, move_amt):
    me = obj.data
    if me.is_editmode:
        bm = bmesh.from_edit_mesh(me)
    else:
        bm = bmesh.new()
        bm.from_mesh(me)
    for v in bm.verts:
        v.co += move_amt
    if bm.is_wrapped:
        bmesh.update_edit_mesh(me, False, False)
    else:
        bm.to_mesh(me)
        me.update()

def set_origin(obj, origin):
    loc, rot, scale = obj.matrix_local.decompose()
    offset = origin - loc
    offset = mathutils.Vector([offset[0] / scale[0], offset[1] / scale[1], offset[2] / scale[2]])
    me = obj.data
    if me.is_editmode:
        bm = bmesh.from_edit_mesh(me)
    else:
        bm = bmesh.new()
        bm.from_mesh(me)
    for v in bm.verts:
        v.co -= offset
    if bm.is_wrapped:
        bmesh.update_edit_mesh(me, False, False)
    else:
        bm.to_mesh(me)
        me.update()
    obj.matrix_local.translation = origin


class BoundingBoxBase:
    def get_dimensions(self):
        return mathutils.Vector(self.box_max) -  mathutils.Vector(self.box_min)
        
    def set_from_object(self, obj):
        coords = [coord[:] for coord in obj.bound_box]
        axis_values = zip(*coords)
        min_vec, max_vec = {}, {}
        for i, values in enumerate(axis_values):
            min_vec[i] = min(values)
            max_vec[i] = max(values)
            self.box_min[i] = min(values)
            self.box_max[i] = max(values)
    
    def get_bottomfrontleft(self): return self.box_min
    def get_bottombackleft(self): return mathutils.Vector([self.box_min[0], self.box_max[1], self.box_min[2]])
    def get_topbackright(self): return self.box_max

    def copy(bounds):
        self.box_min = bounds.box_min
        self.box_max = bounds.box_max
            
    def get_topleft(self):
        return self.topleft

class BoundingBox(BoundingBoxBase):
    def __init__(self, obj):
        self.box_min = mathutils.Vector([0, 0, 0])
        self.box_max = mathutils.Vector([0, 0, 0])
        self.set_from_object(obj) 



class BpyBoundingBox(bpy.types.PropertyGroup, BoundingBoxBase):
    box_min : bpy.props.FloatVectorProperty(size=3, default=[0, 0, 0])
    box_max : bpy.props.FloatVectorProperty(size=3, default=[0, 0, 0])