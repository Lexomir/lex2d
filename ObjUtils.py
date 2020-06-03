import bpy
import bmesh
import mathutils
from .utils import *

def get_bounds(obj):
    return BoundingBox(from_obj=obj)

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

    def set_from_bmesh(self, bm):
        coords = [vert.co[:] for vert in bm.verts]
        axis_values = zip(*coords)
        min_vec, max_vec = {}, {}
        for i, values in enumerate(axis_values):
            min_vec[i] = min(values)
            max_vec[i] = max(values)
            self.box_min[i] = min(values)
            self.box_max[i] = max(values)
    
    def get_bottomfrontleft(self): return mathutils.Vector(self.box_min)
    def get_bottombackleft(self): return mathutils.Vector([self.box_min[0], self.box_max[1], self.box_min[2]])
    def get_topbackright(self): return mathutils.Vector(self.box_max)

    def copy(bounds):
        self.box_min = bounds.box_min
        self.box_max = bounds.box_max
            
    def get_topleft(self):
        return self.topleft

class BoundingBox(BoundingBoxBase):
    def __init__(self, from_obj=None, from_bm=None):
        self.box_min = mathutils.Vector([0, 0, 0])
        self.box_max = mathutils.Vector([0, 0, 0])
        if from_obj:
            self.set_from_object(from_obj) 
        elif from_bm:
            self.set_from_bmesh(from_bm) 


class BpyBoundingBox(bpy.types.PropertyGroup, BoundingBoxBase):
    def copy_into(self, other_bb):
        other_bb.box_min = self.box_min
        other_bb.box_max = self.box_max

    box_min : bpy.props.FloatVectorProperty(size=3, default=[0, 0, 0])
    box_max : bpy.props.FloatVectorProperty(size=3, default=[0, 0, 0])

def set_mesh_preserve_origin(obj, bm):
    original_bb = BoundingBox(from_obj=obj)
    obj_size = original_bb.get_dimensions()
    if obj_size[0] == 0 or obj_size[1] == 0:
        tl = mathutils.Vector([0,0,0])
    else:
        tl = original_bb.get_bottombackleft()
        tl = mathutils.Vector([tl[0] / obj_size[0], tl[1] / obj_size[1], 0])
    new_bb = BoundingBox(from_bm=bm)
    new_size = new_bb.get_dimensions()
    if new_size[0] == 0 or new_size[1] == 0:
        new_tl = mathutils.Vector([0,0,0])
    else:
        new_tl = new_bb.get_bottombackleft()
        new_tl = mathutils.Vector([new_tl[0] / new_size[0], new_tl[1] / new_size[1], 0])
    vert_move_amt = multiply_vec3((tl - new_tl), new_size)
    for v in bm.verts:
        v.co += vert_move_amt
    bm.to_mesh(obj.data)
