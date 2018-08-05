import pathlib
import time
import bpy
from .gltfbuilder import GLTFBuilder
from .to_gltf import to_gltf


def get_objects(selected_only: bool):
    if selected_only:
        return bpy.context.selected_objects
    else:
        return bpy.data.scenes[0].objects


def export(path: pathlib.Path, selected_only: bool):

    # object mode
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    start = time.time()

    #
    # gather items
    #
    builder = GLTFBuilder()
    objects = get_objects(selected_only)
    builder.export_objects(objects)

    #
    # export
    #
    bin_path = path.parent / (path.stem + ".bin")
    gltf, bin = to_gltf(builder, path, bin_path)

    #
    # write
    #
    with path.open('wb') as f:
        f.write(gltf.to_json().encode('utf-8'))
    with bin_path.open('wb') as f:
        f.write(bin)

    elaplsed_time = time.time() - start
    print(f'elaplsed_time: {elaplsed_time}')
