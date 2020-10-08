import bpy
import bpy.utils
import io_scene_yup
io_scene_yup.register()

# run
bpy.ops.export_scene.yup()
