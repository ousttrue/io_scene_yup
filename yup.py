from typing import List
import bpy
import mathutils


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


class Yup:
    def __init__(self):
        self.indent = ' ' * 2

    def export_objects(self, objects: List[bpy.types.Object]):
        for o in objects:
            self.export_object(o)

    def export_object(self, o: bpy.types.Object, indent: str=''):
        print(f'{indent}{o.name}')

        # only mesh
        if o.type == 'MESH':

            store=MeshStore()

            # copy
            new_obj = o.copy()
            new_obj.data = o.data.copy()
            bpy.data.scenes[0].objects.link(new_obj)

            mesh = new_obj.data
            print('copy', new_obj, mesh.vertices)

            # apply modifiers exclude armature

            # rotate to Y-UP

            # export
            mesh.update(calc_tessface=True)
            for i, face in enumerate(mesh.tessfaces):

                if len(face.vertices)==3:
                    # triangle
                    store.add_triangle(
                        mesh.vertices[face.vertices[0]].co,
                        mesh.vertices[face.vertices[1]].co,
                        mesh.vertices[face.vertices[2]].co
                    )
                elif len(face.vertices)==4:
                    # quad
                    store.add_quadrangle(
                        mesh.vertices[face.vertices[0]].co,
                        mesh.vertices[face.vertices[1]].co,
                        mesh.vertices[face.vertices[2]].co,
                        mesh.vertices[face.vertices[3]].co
                    )
                else:
                    raise Exception(f'face.vertices: {len(face.vertices)}')

            print(store.positions)

        for child in o.children:
            self.export_object(child, indent+self.indent)

    def write_to(self, path: str):
        from .gltf import GLTF
        import io

        gltf = GLTF()

        with io.open(path, 'wb') as f:
            f.write(gltf.to_json().encode('utf-8'))


def export(path: str, selected_only: bool):
    yup = Yup()

    # object mode
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    if selected_only:
        yup.export_objects(bpy.context.selected_objects)
    else:
        yup.export_objects(bpy.data.scenes[0].objects)

    yup.write_to(path)
