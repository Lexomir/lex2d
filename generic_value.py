import bpy
from bpy.props import *
from math import inf


def ui_cb(func):
    def wrapped(self, val):
        func(self, val, propagate=True)
    return wrapped

# custom PropertyGroups can inherit from this
class GenericValue:
    def set_generic(self, datatype, val, args):
        if datatype == 'float': return self.set_float(val, args[0], args[1])
        if datatype == 'int': return self.set_int(val, args[0], args[1])
        if datatype == 'string': return self.set_string(val)
        if datatype == 'bool': return self.set_bool(val)
        if datatype == 'enum': return self.set_enum(val, items=args)
        if datatype == 'object': return self.set_object(val)
        if datatype == 'vec2': return self.set_vec2(val)
        if datatype == 'vec3': return self.set_vec3(val)
        if datatype == 'vec4': return self.set_vec4(val)
        raise Exception("bad generic type")

    def set_meta(self, datatype, args):
        self.datatype = datatype
        if datatype == 'float': return self.set_range(args[0], args[1])
        if datatype == 'int': return self.set_range(args[0], args[1])
        if datatype == 'enum': return self._set_enum_items(args)

    def get_args(self):
        if self.datatype == 'float': return [self.min_value, self.max_value]
        if self.datatype == 'int': return [self.min_value, self.max_value]
        if self.datatype == 'enum': return self.enum_items.split(",") or []

    def set_float(self, val, min_value, max_value):
        self.datatype = 'float'
        self.min_value = min_value
        self.max_value = max_value
        self._set_value_as_float(val, propagate=False)
        
    def set_int(self, val, min_value, max_value):
        self.datatype = 'int'
        self.min_value = min_value
        self.max_value = max_value
        self._set_value_as_int(val, propagate=False)

    def set_string(self, val):
        self.datatype = 'string'
        self._set_string_value(val, propagate=False)

    def set_bool(self, val):
        self.datatype = 'bool'
        self._set_value_as_bool(val, propagate=False)

    def set_enum(self, val, items):
        self.datatype = 'enum'
        self.enum_items = ",".join(items)
        self._set_value_as_enum(val, propagate=False)

    def set_object(self, obj_name):
        self.datatype = 'object'
        self._set_string_value(obj_name, propagate=False)
    
    def set_vec2(self, val):
        self.datatype = 'vec2'
        self._set_value_as_vec4([val[0], val[1], 0, 0])
    
    def set_vec3(self, val):
        self.datatype = 'vec3'
        self._set_value_as_vec4([val[0], val[1], val[2], 0])
        
    def set_vec4(self, val):
        self.datatype = 'vec4'
        self._set_value_as_vec4([val[0], val[1], val[2], val[3]])

    def set_range(self, min_value, max_value):
        self.min_value = min_value
        self.max_value = max_value

    def get_float(self): return self._get_value_as_float()
    def get_int(self): return self._get_value_as_int()
    def get_bool(self): return self._get_value_as_bool()
    def get_string(self): return self.string_value
    def get_enum(self): return self._get_value_as_enum()
    def get_object(self): return bpy.data.objects.get(self.string_value, None)
    def get_vec2(self): return self._get_value_as_vec4()[0:2]
    def get_vec3(self): return self._get_value_as_vec4()[0:3]
    def get_vec4(self): return self._get_value_as_vec4()


    def set_value(self, val):
        if self.datatype == 'int': return self._set_value_as_int(val)
        elif self.datatype == 'float': return self._set_value_as_float(val)
        elif self.datatype == 'object': return self._set_string_value(val.name)
        elif self.datatype == 'bool': return self._set_value_as_bool(val)
        elif self.datatype == 'string': return self._set_string_value(val)
        elif self.datatype == 'enum': return self._set_string_value(val)
        elif self.datatype == 'vec2': return self._set_value_as_vec4([val[0], val[1], 0, 0])
        elif self.datatype == 'vec3': return self._set_value_as_vec4([val[0], val[1], val[2], 0])
        elif self.datatype == 'vec4': return self._set_value_as_vec4(val)
        else: raise ValueError("Oh NO: '{}'".format(self.datatype))

    def get_value(self):
        if self.datatype == 'int': return self.get_int()
        elif self.datatype == 'float': return self.get_float()
        elif self.datatype == 'object': return self.get_object()
        elif self.datatype == 'bool': return self.get_bool()
        elif self.datatype == 'string': return self.get_string()
        elif self.datatype == 'enum': return self.get_string()
        elif self.datatype == 'vec2': return self.get_vec2()
        elif self.datatype == 'vec3': return self.get_vec3()
        elif self.datatype == 'vec4': return self.get_vec4()
        else: raise ValueError("Oh NO: '{}'".format(self.datatype))

    def valid(self):
        if self.datatype == "": return False
        elif self.datatype == 'enum' and self.string_value not in self._get_enum_items(): return False
        elif self.datatype in ['float', 'int']: return self.min_value <= self.get_value() <= self.max_value
        elif 'vec' in self.datatype: return len(self.get_string().split(',')) == 4
        else:
            return True

    
    def draw(self, layout, context):
        if self.datatype == 'bool':
            layout.prop(self, "bool_value", text=self.name)
        elif self.datatype == 'float':
            layout.prop(self, "float_value", text=self.name)
        elif self.datatype == 'string':
            layout.prop(self, "string_value", text=self.name)
        elif self.datatype == 'int':
            layout.prop(self, "int_value", text=self.name)
        elif self.datatype == 'enum':
            layout.prop(self, "enum_value", text=self.name)
        elif self.datatype == 'object':
            layout.prop_search(self, "string_value", context.scene, "objects", icon = "NONE", text=self.name)
        elif self.datatype == 'vec2':
            row = layout.row(align=True)
            row.label(text=self.name)
            row.prop(self, "vec_value", text="", index=0)
            row.prop(self, "vec_value", text="", index=1)
        elif self.datatype == 'vec3':
            row = layout.row(align=True)
            row.label(text=self.name)
            row.prop(self, "vec_value", text="", index=0)
            row.prop(self, "vec_value", text="", index=1)
            row.prop(self, "vec_value", text="", index=2)
        elif self.datatype == 'vec4':
            row = layout.row(align=True)
            row.label(text=self.name)
            row.prop(self, "vec_value", text="", index=0)
            row.prop(self, "vec_value", text="", index=1)
            row.prop(self, "vec_value", text="", index=2)
            row.prop(self, "vec_value", text="", index=3)

    # override
    def on_value_updated(self, prev_value, curr_value):
        pass

    # internal
    def _get_value_as_bool(self):
        return bool(self.string_value)

    def _set_value_as_bool(self, val, propagate=False):
        self._set_string_value(str(val) if val else "", propagate=propagate)

    def _get_value_as_float(self):
        val = 0
        try: val = float(self.string_value)
        finally: return val

    def _set_value_as_float(self, val, propagate=False):
        val = max(self.min_value, min(val, self.max_value))
        str_val = str(val)
        if str_val != self.string_value:
            self._set_string_value(str_val, propagate=propagate)

    def _get_value_as_int(self):
        val = 0
        try: val = int(round(float(self.string_value)))
        finally: return val

    def _set_value_as_int(self, val, propagate=False):
        val = max(self.min_value, min(val, self.max_value))
        str_val = str(val)
        if str_val != self.string_value:
            self._set_string_value(str_val, propagate=propagate)

    def _set_value_as_enum(self, val, propagate=False):
        items = self.enum_items.split(",")
        for i, item in enumerate(items):
            if i == val:
                self._set_string_value(item, propagate=propagate)

    def _get_value_as_enum(self):
        items = self.enum_items.split(",")
        for i, item in enumerate(items):
            if item == self.string_value:
                return i
        return -1

    def _set_value_as_vec4(self, val, propagate=False):
        vec4_str = [str(val[0]), str(val[1]), str(val[2]), str(val[3])]
        self._set_string_value(",".join(vec4_str), propagate=propagate)
        
    def _get_value_as_vec4(self):
        def parse_float(str):
            val = 0
            try: val = float(str)
            finally: return val
        float_strs = self.string_value.split(',')
        assert(len(float_strs) == 4)
        return [parse_float(float_str) for float_str in float_strs]

    def _get_bpy_enum_items(self, context=None):
        items = self.enum_items.split(",")
        return [(item, item, item) for item in items]

    def _get_enum_items(self):
        return self.enum_items.split(",")

    def _set_enum_items(self, items):
        self.enum_items = ",".join(items)

    def _set_string_value(self, value, propagate=False):
        prev_value = self['string_value'] if 'string_value' in self else ""
        self['string_value'] = value
        if propagate:
            self.on_value_updated(prev_value, value)

    def _get_string_value(self):
        return self['string_value'] if 'string_value' in self else ""


    # properties
    string_value : StringProperty(default="", set=ui_cb(_set_string_value), get=_get_string_value)
    bool_value : BoolProperty(get=_get_value_as_bool, set=ui_cb(_set_value_as_bool))
    float_value : FloatProperty(get=_get_value_as_float, set=ui_cb(_set_value_as_float))
    int_value : IntProperty(get=_get_value_as_int, set=ui_cb(_set_value_as_int))
    enum_value : EnumProperty(get=_get_value_as_enum, set=ui_cb(_set_value_as_enum), items=_get_bpy_enum_items)
    vec_value : FloatVectorProperty(get=_get_value_as_vec4, set=ui_cb(_set_value_as_vec4), size=4)
    enum_items : StringProperty()
    datatype : StringProperty(default='invalid')
    min_value : FloatProperty()
    max_value : FloatProperty()
    datatype : StringProperty()
