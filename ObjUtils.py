import bpy
import bmesh
import mathutils

def get_bounds(obj):
    return BoundingBox(obj)

def set_origin(obj, origin):
    offset = origin - obj.location
    offset = mathutils.Vector([offset[0] / obj.scale[0], offset[1] / obj.scale[1], offset[2] / obj.scale[2]])
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for v in bm.verts:
        v.co -= offset
    bm.to_mesh(obj.data)
    obj.data.update()
    obj.location = origin


class BoundingBoxBase:
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