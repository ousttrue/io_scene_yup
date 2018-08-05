import pathlib
import time
import bpy
import struct
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

    ext = path.suffix.lower()

    #
    # export
    #
    bin_path = path.parent / (path.stem + ".bin")
    gltf, bin_bytes = to_gltf(builder, path, bin_path if ext!='.glb' else None)

    #
    # write
    #
    json_bytes = gltf.to_json().encode('utf-8')

    if ext == '.gltf':
        with path.open('wb') as f:
            f.write(json_bytes)
        with bin_path.open('wb') as f:
            f.write(bin_bytes)
    elif ext == '.glb':
        with path.open('wb') as f:
            if len(json_bytes)%4!=0:
                json_padding_size = (4 - len(json_bytes) % 4)
                print(f'add json_padding_size: {json_padding_size}')
                json_bytes += b' ' * json_padding_size
            json_header =  struct.pack(b'I', len(json_bytes)) + b'JSON'
            bin_header = struct.pack(b'I', len(bin_bytes)) + b'BIN\x00'
            header = b'glTF' + struct.pack('II', 2, 12+len(json_header)+len(json_bytes)+len(bin_header)+len(bin_bytes))
            #
            f.write(header)
            f.write(json_header)
            f.write(json_bytes)
            f.write(bin_header)
            f.write(bin_bytes)
    else:
        raise NotImplementedError()

    elaplsed_time = time.time() - start
    print(f'elaplsed_time: {elaplsed_time}')
