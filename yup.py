from typing import List
import bpy


class Yup:
    def __init__(self):
        pass

    def export_objects(self, objects: List[bpy.types.Object]):
        for o in objects:
            self.export_object(o)

    def export_object(self, o: bpy.types.Object):
        # only mesh
        if o.type != 'MESH':
            return

        # copy
        new_obj = o.copy()
        bpy.data.scenes[0].objects.link(new_obj)
        print('copy', new_obj)

        # apply modifiers exclude armature

        # rotate to Y-UP

        # export

    def write_to(self, path: str):
        print(path)


def export(path: str, selected_only: bool):
    yup = Yup()

    # object mode
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    if selected_only:
        yup.export_objects(bpy.context.selected_objects)
    else:
        yup.export_objects(bpy.data.scenes[0].objects)

    yup.write_to(path)
