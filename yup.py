import bpy
import mathutils
import array
import io
import pathlib
from typing import List, NamedTuple
from . import gltf
from .binarybuffer import BinaryBuffer


class MeshStore:

    def __init__(self, name: str)->None:
        self.name = name
        self.positions: array.array = array.array('f')
        self.indices: array.array = array.array('I')

    def add_vertex(self, v: mathutils.Vector):
        self.positions.append(v.x)
        self.positions.append(v.y)
        self.positions.append(v.z)

    def add_triangle(self, t0: mathutils.Vector, t1: mathutils.Vector, t2: mathutils.Vector):
        index = int(len(self.positions)/3)
        self.add_vertex(t0)
        self.add_vertex(t1)
        self.add_vertex(t2)
        self.indices.append(index)
        self.indices.append(index+1)
        self.indices.append(index+2)

    def add_quadrangle(self, t0, t1, t2, t3):
        index = int(len(self.positions)/3)
        self.add_vertex(t0)
        self.add_vertex(t1)
        self.add_vertex(t2)
        self.add_vertex(t3)

        self.indices.append(index)
        self.indices.append(index+1)
        self.indices.append(index+2)

        self.indices.append(index+2)
        self.indices.append(index+3)
        self.indices.append(index)


class GLTFBuilder:
    def __init__(self):
        self.gltf = gltf.GLTF()
        self.indent = ' ' * 2
        self.meshes: List[MeshStore] = []
        self.buffers: List[BinaryBuffer] = []
        self.views: List[gltf.GLTFBufferView] = []
        self.accessors: List[gltf.GLTFAccessor] = []

    def export_object(self, o: bpy.types.Object, indent: str=''):
        print(f'{indent}{o.name}')

        # only mesh
        if o.type == 'MESH':

            # copy
            new_obj = o.copy()
            new_obj.data = o.data.copy()
            bpy.data.scenes[0].objects.link(new_obj)

            mesh = new_obj.data

            # apply modifiers exclude armature

            # rotate to Y-UP

            # export
            self.export_mesh(mesh)

        for child in o.children:
            self.export_object(child, indent+self.indent)

    def export_mesh(self, mesh: bpy.types.Mesh):

        mesh.update(calc_tessface=True)
        store = MeshStore(mesh.name)
        for i, face in enumerate(mesh.tessfaces):

            if len(face.vertices) == 3:
                # triangle
                store.add_triangle(
                    mesh.vertices[face.vertices[0]].co,
                    mesh.vertices[face.vertices[1]].co,
                    mesh.vertices[face.vertices[2]].co
                )
            elif len(face.vertices) == 4:
                # quad
                store.add_quadrangle(
                    mesh.vertices[face.vertices[0]].co,
                    mesh.vertices[face.vertices[1]].co,
                    mesh.vertices[face.vertices[2]].co,
                    mesh.vertices[face.vertices[3]].co
                )
            else:
                raise Exception(f'face.vertices: {len(face.vertices)}')

        self.meshes.append(store)

    def add_buffer(self, path: pathlib.Path)->int:
        index = len(self.buffers)
        self.buffers.append(BinaryBuffer(index))
        return index

    def push_bytes(self, buffer_index: int, data: array.array, element_count: int)->int:
        # append view
        view_index = len(self.views)
        view = self.buffers[buffer_index].append(data.tobytes())
        self.views.append(view)
        # append accessor
        accessor_index = len(self.accessors)
        accessor = gltf.GLTFAccessor(
            bufferView=view_index,
            byteOffset=0,
            componentType=gltf.format_to_componentType(data.typecode),
            type=gltf.GLTFAccessorType(element_count),
            count=int(len(data)/element_count)
        )
        self.accessors.append(accessor)
        return accessor_index

    def write_to(self, gltf_path: pathlib.Path):
        # create buffer
        bin_path = gltf_path.parent / (gltf_path.stem + ".bin")
        buffer_index = self.add_buffer(bin_path)

        meshes: List[gltf.GLTFMesh] = []
        for mesh in self.meshes:
            position_accessor_index = self.push_bytes(
                buffer_index, mesh.positions, 3)
            indices_accessor_index = self.push_bytes(
                buffer_index, mesh.indices, 1)
            #print(position_accessor_index, indices_accessor_index)
            gltf_mesh = gltf.GLTFMesh(
                name=mesh.name,
                primitives=[
                    gltf.GLTFMeshPrimitive(
                        attributes={
                            'POSITION': position_accessor_index
                        },
                        indices=indices_accessor_index,
                        material=-1,
                        mode=gltf.GLTFMeshPrimitiveTopology.TRIANGLES,
                        targets=[]
                    )
                ]
            )
            meshes.append(gltf_mesh)

        uri = bin_path.relative_to(gltf_path.parent)
        gltf_root = gltf.GLTF(
            buffers=[gltf.GLTFBUffer(str(uri), len(self.buffers[0].data))],
            bufferViews=self.views,
            accessors=self.accessors,
            meshes=meshes
        )

        # write bin
        with bin_path.open('wb') as f:
            f.write(self.buffers[buffer_index].data)

        # write gltf
        with gltf_path.open('wb') as f:
            f.write(gltf_root.to_json().encode('utf-8'))


def get_objects(selected_only: bool):
    if selected_only:
        return bpy.context.selected_objects
    else:
        return bpy.data.scenes[0].objects


def export(path: pathlib.Path, selected_only: bool):

    # object mode
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    objects = get_objects(selected_only)

    builder = GLTFBuilder()
    for o in objects:
        builder.export_object(o)

    builder.write_to(path)
