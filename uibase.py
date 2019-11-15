import bpy


class LexBaseListAction:
    action : bpy.props.EnumProperty(
        items=[
            ('UP', "Up", ""),
            ('DOWN', "Down", ""),
            ('REMOVE', "Remove", ""),
            ('ADD', "Add", ""),
        ]
    )

    shift : bpy.props.BoolProperty()
    ctrl : bpy.props.BoolProperty()

    def get_collection(self): return []

    def get_index_property(self): return ""

    def get_index_source(self): return []

    def move_item(self, old_index, new_index):
        collection = self.get_collection()
        collection.move(old_index, new_index)

    def new_item(self):
        collection = self.get_collection()
        item = collection.add()
        self.set_index(len(collection) - 1, propagate=True)
        return item
    
    def remove_item(self, idx):
        collection = self.get_collection()
        new_idx = idx
        if idx != 0 or len(collection) == 1:
            new_idx -= 1
        self.set_index(idx - 1, propagate=True)
        collection.remove(idx)

    # return "should continue executing?""
    def on_execute(self, context): 
        return True
    
    # arg: propagate (should this trigger callbacks) -- e.g. moving an item up and down shouldn't be considered a selection change
    def set_index(self, index, propagate): 
        index_src = self.get_index_source()
        index_property_name = self.get_index_property()
        setattr(index_src, index_property_name, index)

    def get_index(self):
        collection = self.get_collection()
        index_src = self.get_index_source()
        index_property_name = self.get_index_property()
        return getattr(index_src, index_property_name)

    def invoke(self, context, event):
        self.shift = event.shift
        self.ctrl = event.ctrl
        return self.execute(context)

    def execute(self, context):
        should_continue = self.on_execute(context)
        if not should_continue:
            return {"CANCELLED"}

        collection = self.get_collection()
        idx = self.get_index()

        # TODO get item function
        item = collection[idx] if 0 <= idx < len(collection) else None

        if self.action == 'DOWN' and idx < len(collection) - 1:
            self.move_item(idx, idx + 1)
            self.set_index(idx + 1, propagate=False)
        elif self.action == 'UP' and idx >= 1:
            item_prev = collection[idx - 1]
            self.move_item(idx, idx - 1)
            self.set_index(idx - 1, propagate=False)
        elif self.action == 'REMOVE' and item:
            self.remove_item(idx)
        elif self.action == 'ADD':
            self.new_item()
        return {"FINISHED"}
