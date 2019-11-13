import bpy
import blf
import os
import gpu
from gpu_extras.batch import batch_for_shader

TEXT_INPUT_PADDING = 3
DIALOG_PADDING = 8
WIDGET_PADDING = DIALOG_PADDING + 15

symbol_to_char = {
    'ZERO' : ('0', ')'),
    'ONE' : ('1', '!'),
    'TWO' : ('2', '@'),
    'THREE' : ('3', '#'),
    'FOUR' : ('4', '$'),
    'FIVE' : ('5', '%'),
    'SIX' : ('6', '^'),
    'SEVEN' : ('7', '&'),
    'EIGHT' : ('8', '*'),
    'NINE' : ('9','('),
    'PERIOD' : ('.', '>'),
    'MINUS' : ('-', '_'),
    'PLUS' : ('+', '='),
    'EQUALS' : ('=', '+'),
    'SPACE' : (' ', ' '),
}
numpad_to_char = {
    'NUMPAD_0' : '0',
    'NUMPAD_1' : '1',
    'NUMPAD_2' : '2',
    'NUMPAD_3' : '3',
    'NUMPAD_4' : '4',
    'NUMPAD_5' : '5',
    'NUMPAD_6' : '6',
    'NUMPAD_7' : '7',
    'NUMPAD_8' : '8',
    'NUMPAD_9' : '9',
    'NUMPAD_PERIOD' : '.',
    'NUMPAD_MINUS' : '-',
    'NUMPAD_PLUS' : '+',
    'NUMPAD_ASTERIX' : '*',
    'NUMPAD_ENTER' : None,
    'NUMPAD_SLASH' : '/',
}

def parse_char_input(event):
    if len(event.type) == 1 and event.value == "PRESS":
        return event.type if event.shift else event.type.lower()
    elif event.type in symbol_to_char:
        return symbol_to_char[event.type][1] if event.shift else symbol_to_char[event.type][0]
    elif event.type[:6] == 'NUMPAD' and event.value == "PRESS":
        return numpad_to_char[event.type]
    return None

#TODO optimize = use caching instead (would fix imprecision too)
# each letter caches the length to the start of the line
def text_position(target_x, text, fontid):
    debug = ""
    if target_x <= 0:
        return 0, 0
    start_x = 0
    searchstart = 0
    searchend = len(text)
    done = False
    while not done:
        searchmid = searchstart + int((searchend - searchstart) * .5 + .5)
        w, h = blf.dimensions(fontid, text[searchstart:searchmid])
        debug += "({}:{} = {} + {}), ".format(searchstart, searchmid, int(start_x), int(w))
        if searchend <= searchstart + 1:
            if int(target_x + w*.5) >= start_x + w:
                return int(start_x + w), searchstart + 1
            else:                
                return int(start_x), searchstart
        if target_x >= start_x + w:
            searchstart = searchmid
            start_x += w
        else:
            searchend = searchmid

def process_event(self, context, event):
    blf.size(0, 12, 72)
    widget_x = self.pos[0] + self.widget_pos[0]
    if event.type == "MOUSEMOVE":
        if self.mousedown_on_widget:
            new_char_px, new_char_idx = text_position(event.mouse_region_x - widget_x - TEXT_INPUT_PADDING, self.name, 0)
            self.cursor_char_idx = new_char_idx
            self.cursor_char_x = new_char_px
            if new_char_idx > self.mousedown_char_idx:
                self.selection_px = (self.mousedown_char_x, new_char_px)
                self.selection_idx = (self.mousedown_char_idx, new_char_idx)
            else:
                self.selection_px = (new_char_px, self.mousedown_char_x)
                self.selection_idx = (new_char_idx, self.mousedown_char_idx)
            print("({}, {})".format(self.selection_idx[0], self.selection_idx[1]))
    elif event.type == "LEFTMOUSE" and event.value == "RELEASE":
        self.mousedown_on_widget = False
    elif event.type == "LEFTMOUSE" and event.value == "PRESS":
        self.cursor_blink = False
        self.mousedown_on_widget = True
        self.mousedown_char_x, self.mousedown_char_idx = text_position(event.mouse_region_x - widget_x - TEXT_INPUT_PADDING, self.name, 0)
        self.cursor_char_x, self.cursor_char_idx = self.mousedown_char_x, self.mousedown_char_idx
        self.selection_idx = (self.cursor_char_idx,self.cursor_char_idx)
        self.selection_px = (self.cursor_char_x,self.cursor_char_x)
        print(self.mousedown_char_x, len(self.name) - 1)
    elif event.type == "TIMER":
        self.cursor_blink = not self.cursor_blink
    elif event.type in {'ESC'}:
        return {'CANCELLED'}
    elif event.type == "LEFT_ARROW" and event.value == "PRESS":
        self.cursor_blink = False
        tmp = self.cursor_char_idx
        new_idx = 0 if event.ctrl else self.cursor_char_idx - 1
        new_idx = max(0, new_idx)
        new_px = blf.dimensions(0, self.name[:new_idx])[0]
        if event.shift:
            if self.selection_idx[1] == self.cursor_char_idx:
                self.selection_idx[1] = new_idx
                self.selection_px[1] = blf.dimensions(0, self.name[:self.selection_idx[1]])[0]
            else:
                self.selection_idx[0] = new_idx
                self.selection_px[0] = blf.dimensions(0, self.name[:self.selection_idx[0]])[0]
            if self.selection_idx[0] > self.selection_idx[1]:
                self.selection_idx = (self.selection_idx[1], self.selection_idx[0])
                self.selection_px = (self.selection_px[1], self.selection_px[0])
        else:
            if self.selection_idx[0] != self.selection_idx[1]:
                new_idx = self.selection_idx[0]
                new_px = self.selection_px[0]
            self.selection_idx = (new_idx, new_idx)
            self.selection_px = (int(new_px), int(new_px))
        self.cursor_char_idx = new_idx
        self.cursor_char_x = new_px
        
    elif event.type == "RIGHT_ARROW" and event.value == "PRESS":
        self.cursor_blink = False
        tmp = self.cursor_char_idx
        new_idx = len(self.name) if event.ctrl else self.cursor_char_idx + 1
        new_idx = min(len(self.name), new_idx)
        new_px = blf.dimensions(0, self.name[:new_idx])[0]
        if event.shift:
            if self.selection_idx[1] == self.cursor_char_idx:
                self.selection_idx[1] = new_idx
                self.selection_px[1] = blf.dimensions(0, self.name[:self.selection_idx[1]])[0]
            else:
                self.selection_idx[0] = new_idx
                self.selection_px[0] = blf.dimensions(0, self.name[:self.selection_idx[0]])[0]
            if self.selection_idx[0] > self.selection_idx[1]:
                self.selection_idx = (self.selection_idx[1], self.selection_idx[0])
                self.selection_px = (self.selection_px[1], self.selection_px[0])
        else:
            if self.selection_idx[0] != self.selection_idx[1]:
                new_idx = self.selection_idx[1]
                new_px = self.selection_px[1]
            self.selection_idx = (new_idx, new_idx)
            self.selection_px = (int(new_px), int(new_px))
        self.cursor_char_idx = new_idx
        self.cursor_char_x = new_px
    elif event.type == "DEL" and event.value == "PRESS":
        self.cursor_blink = False
        if self.selection_idx[0] != self.selection_idx[1]:
            self.name = self.name[:self.selection_idx[0]] + self.name[self.selection_idx[1]:]
            self.cursor_char_idx = self.selection_idx[0]
            self.cursor_char_x = self.selection_px[0]
        else:
            delete_to_idx = len(self.name) if event.ctrl else min(self.cursor_char_idx + 1, len(self.name))
            self.name = self.name[: self.cursor_char_idx] + self.name[delete_to_idx :]
            self.cursor_char_x = blf.dimensions(0, self.name[:self.cursor_char_idx])[0]
        self.selection_idx = (self.cursor_char_idx, self.cursor_char_idx)
        self.selection_px = (self.cursor_char_x, self.cursor_char_x)
    elif event.type == "BACK_SPACE" and event.value == "PRESS":
        self.cursor_blink = False
        if self.selection_idx[0] != self.selection_idx[1]:
            self.name = self.name[:self.selection_idx[0]] + self.name[self.selection_idx[1]:]
            self.cursor_char_idx = self.selection_idx[0]
            self.cursor_char_x = self.selection_px[0]
        else:
            delete_amount = self.cursor_char_idx if event.ctrl else 1
            self.name = self.name[: self.cursor_char_idx - delete_amount] + self.name[self.cursor_char_idx :]
            self.cursor_char_idx = max(0, self.cursor_char_idx - delete_amount)
            self.cursor_char_x = blf.dimensions(0, self.name[:self.cursor_char_idx])[0]
        self.selection_idx = (self.cursor_char_idx, self.cursor_char_idx)
        self.selection_px = (self.cursor_char_x, self.cursor_char_x)
    else:
        ch = parse_char_input(event)
        if ch and ch not in "&^%$#@*+={}[]\":;/?\\<>,'":
            print("typed {} {} {}".format(ch, self.selection_idx[0] != self.selection_idx[1], self.cursor_char_idx))
            if self.selection_idx[0] != self.selection_idx[1]:
                self.name = self.name[:self.selection_idx[0]] + self.name[self.selection_idx[1]:]
                self.cursor_char_idx = self.selection_idx[0]
                self.cursor_char_x = self.selection_px[0]
            self.cursor_blink = False
            self.name = self.name[:self.cursor_char_idx] + ch + self.name[self.cursor_char_idx:]
            self.cursor_char_idx += 1
            self.cursor_char_x = blf.dimensions(0, self.name[:self.cursor_char_idx])[0]
            self.selection_idx = (self.cursor_char_idx, self.cursor_char_idx)
            self.selection_px = (self.cursor_char_x, self.cursor_char_x)
    return {'RUNNING_MODAL'}

class TextBoxDialog(bpy.types.Operator):
    bl_idname = "example.textbox_dialog"
    bl_label = "Custom TextBox Dialog"

    def modal(self, context, event):
        self.pos = [100, 200]
        self.size = [200, DIALOG_PADDING*3 + 18 + 12]
        self.widget_pos = [WIDGET_PADDING, DIALOG_PADDING]
        self.widget_size = [200-WIDGET_PADDING-DIALOG_PADDING, 18]
        
        refresh_screen_area("VIEW_3D")
        result = process_event(self, context, event)
        if result in {"FINISHED", "CANCELLED"}:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            context.window_manager.event_timer_remove(self._timer)
        
    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        self._timer = context.window_manager.event_timer_add(time_step=0.7, window=context.window)
        self._handle = bpy.types.SpaceView3D.draw_handler_add(_dialog_draw_callback_px, (self, context), 'WINDOW', 'POST_PIXEL')
        return {'RUNNING_MODAL'}

    pos : bpy.props.IntVectorProperty(size=2)
    size : bpy.props.IntVectorProperty(size=2)
    widget_pos : bpy.props.IntVectorProperty(size=2)
    widget_size : bpy.props.IntVectorProperty(size=2)
    mousedown_on_widget : bpy.props.BoolProperty(default=False)
    cursor_blink : bpy.props.BoolProperty(default=False)
    cursor_char_x : bpy.props.IntProperty()
    cursor_char_idx : bpy.props.IntProperty()
    selection_idx : bpy.props.IntVectorProperty(size=2)
    selection_px : bpy.props.IntVectorProperty(size=2)


# Rendering 


vertices = (
    (0, 1), # tl
    (0, 0), # bl
    (1, 0), # br
    (1, 1)) # tr

indices = (
    (0, 1, 2), (2, 3, 0))


def get_vertex_shader():
    vert_filepath = os.path.normpath(os.path.abspath(os.path.dirname(__file__) + "/dialog_shader.vert"))
    with open(vert_filepath, "r") as vert_file:
        vert_shader = vert_file.read()
    return vert_shader

def get_fragment_shader():
    frag_filepath = os.path.normpath(os.path.abspath(os.path.dirname(__file__) + "/dialog_shader.frag"))
    with open(frag_filepath, "r") as frag_file:
        frag_shader = frag_file.read()
    return frag_shader

shader = gpu.types.GPUShader(get_vertex_shader(), get_fragment_shader())
batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)

font_info = {
    "font_id": 0,
    "handler": None,
}

def draw_box(x, y, w, h, color=(0.0, 0.0, 0.0, 1.0)):
    shader.bind()
    shader.uniform_float("color", color)
    shader.uniform_float("DialogPosition", (x, y))
    shader.uniform_float("DialogSize", (w, h))
    batch.draw(shader)

def _dialog_draw_callback_px(op, context):
    # dialog background
    draw_box(op.pos[0], op.pos[1], *op.size, (0.11, 0.11, 0.11, 1))
    # dialog header text
    font_id = font_info["font_id"]
    blf.position(font_id, op.pos[0] + DIALOG_PADDING, op.pos[1] + op.size[1] - 10 - DIALOG_PADDING, 0)
    blf.size(font_id, 12, 72)
    blf.draw(font_id, "Rename")
    # textbox background
    draw_box(op.pos[0] + op.widget_pos[0], op.pos[1] + op.widget_pos[1], *op.widget_size, (0.2, 0.2, 0.2, 1))
    # selection highlight
    if op.selection_idx[0] != op.selection_idx[1]:
        draw_box(op.pos[0] + op.widget_pos[0] + op.selection_px[0] + TEXT_INPUT_PADDING, op.pos[1] + op.widget_pos[1], op.selection_px[1] - op.selection_px[0], op.widget_size[1], (0, 0.2, 0.4, 1))
    # cursor
    if not op.cursor_blink:
        draw_box(op.pos[0] + op.widget_pos[0] + op.cursor_char_x + TEXT_INPUT_PADDING, op.pos[1] + op.widget_pos[1], 1, op.widget_size[1], (1, 1, 1, 1))
    # textbox text
    blf.position(font_id, op.pos[0] + op.widget_pos[0] + TEXT_INPUT_PADDING, op.pos[1] + op.widget_pos[1] + TEXT_INPUT_PADDING, 0)
    blf.size(font_id, 12, 72)
    blf.draw(font_id, op.name)