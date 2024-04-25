bl_info = {
    "name": "yup gltf exporter",
    "author": "ousttrue",
    "version": (0, 1),
    "blender": (2, 83, 0),
    "location": "File > Export > yup gltf-2.0(.gltf)",
    "description": "yup gltf exporter",
    "warning": "",
    "support": "COMMUNITY",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import-Export",
}

if "bpy" in locals():
    import importlib

    if "yup" in locals():
        importlib.reload(yup)  # type: ignore

import bpy
from bpy.props import BoolProperty
from bpy.props import EnumProperty
from bpy.props import StringProperty


class ExportYUP(bpy.types.Operator):
    """Export selection to YUP"""

    bl_idname = "export_scene.yup"
    bl_label = "Export YUP GLTF"

    filepath = StringProperty(subtype="FILE_PATH")

    # Export options

    selectedonly = BoolProperty(
        name="Export Selected Objects Only",
        description="Export only selected objects",
        default=True,
    )

    def execute(self, context):
        import os
        import pathlib

        ext = os.path.splitext(self.filepath)[1].lower()
        if ext != ".gltf" and ext != ".glb":
            self.filepath = bpy.path.ensure_ext(self.filepath, ".gltf")
        path = pathlib.Path(self.filepath).absolute()

        from . import yup

        yup.export(path, self.selectedonly)

        return {"FINISHED"}

    def invoke(self, context, event):
        if not self.filepath:
            self.filepath = bpy.path.ensure_ext(bpy.data.filepath, ".gltf")
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


def menu_func(self, context):
    self.layout.operator(ExportYUP.bl_idname, text="YUP GLTF (.gltf)")


CLASSES = [ExportYUP]


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)

    bpy.types.TOPBAR_MT_file_export.append(menu_func)


def unregister():
    for c in CLASSES:
        bpy.utils.unregister_class(c)

    bpy.types.TOPBAR_MT_file_export.remove(menu_func)


if __name__ == "__main__":
    register()
