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

    def on_add(self, added_item): pass

    def on_remove(self, removed_item): pass

    def execute(self, context):
        collection = self.get_collection()
        index_src = self.get_index_source()
        index_property_name = self.get_index_property()
        idx = getattr(index_src, index_property_name)

        item = collection[idx] if 0 <= idx < len(collection) else None

        if self.action == 'DOWN' and idx < len(collection) - 1:
            collection.move(idx, idx + 1)
            setattr(index_src, index_property_name, idx + 1)
        elif self.action == 'UP' and idx >= 1:
            item_prev = collection[idx - 1]
            collection.move(idx, idx - 1)
            setattr(index_src, index_property_name, idx - 1)
        elif self.action == 'REMOVE' and item:
            if idx != 0 or len(collection) == 1:
                setattr(index_src, index_property_name, idx - 1)
            self.on_remove(item)
            collection.remove(idx)
        elif self.action == 'ADD':
            item = collection.add()
            item.name = ""
            self.on_add(item)
            setattr(index_src, index_property_name, len(collection) - 1)
        return {"FINISHED"}