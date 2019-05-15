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

    def get_collection(self): return []

    def get_index_property(self): return ""

    def get_index_source(self): return []

    def move_item(self, old_index, new_index):
        collection = self.get_collection()
        collection.move(old_index, new_index)

    def new_item(self):
        collection = self.get_collection()
        return collection.add()
    
    def remove_item(self, index):
        collection = self.get_collection()
        collection.remove(index)

    def on_add(self, added_item): pass

    def on_remove(self, removed_item): pass
    
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

    def execute(self, context):
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
            if idx != 0 or len(collection) == 1:
                self.set_index(idx - 1, propagate=True)
            self.on_remove(item)
            self.remove_item(idx)
        elif self.action == 'ADD':
            item = self.new_item()
            self.on_add(item)
            self.set_index(len(collection) - 1, propagate=True)
        return {"FINISHED"}