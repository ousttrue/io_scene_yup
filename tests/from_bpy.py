import bpy
import bpy.utils
import pathlib
import sys

HERE = pathlib.Path(__file__).absolute().parent
sys.path.append(HERE.parent.parent)

import io_scene_yup
io_scene_yup.register()

# run
bpy.ops.export_scene.yup()
