from typing import List
import bpy
import mathutils
from . import gltf


class MeshStore:

    def __init__(self):
        self.positions: List[mathutils.Vector] = []

    def add_triangle(self, t0: mathutils.Vector, t1: mathutils.Vector, t2: mathutils.Vector):
        self.positions.append(t0)
        self.positions.append(t1)
        self.positions.append(t2)

    def add_quadrangle(self, t0, t1, t2, t3):
        self.add_triangle(t0, t1, t2)
        self.add_triangle(t2, t3, t0)

    def to_gltf(self)-> gltf.GLTFMesh:
        return gltf.GLTFMesh(
            name='mesh',
            primitives=[
                gltf.GLTFMeshPrimitive(
                    attributes={
                    },
                    indices=-1,
                    material=-1,
                    mode=gltf.GLTFMeshPrimitiveTopology.TRIANGLES,
                    targets=[]
                )
            ]
        )


class GLTFBuilder:
    def __init__(self):
        self.gltf = gltf.GLTF()
        self.indent = ' ' * 2

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
        store = MeshStore()
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

        self.gltf.meshes.append(store.to_gltf())


def get_objects(selected_only: bool):
    if selected_only:
        return bpy.context.selected_objects
    else:
        return bpy.data.scenes[0].objects


def export(path: str, selected_only: bool):

    # object mode
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    objects = get_objects(selected_only)

    builder = GLTFBuilder()
    for o in objects:
        builder.export_object(o)

    import io
    with io.open(path, 'wb') as f:
        f.write(builder.gltf.to_json().encode('utf-8'))
