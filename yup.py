import bpy
import mathutils
import array
import io
import pathlib
from typing import List, NamedTuple, Optional, Dict
from . import gltf
from .binarybuffer import BinaryBuffer
from .meshstore import MeshStore
from .buffermanager import BufferManager
from .materialstore import MaterialStore


class GLTFBuilderNode:
    def __init__(self, index: int, name: str)->None:
        self.index = index
        self.name = name
        self.children: List[GLTFBuilderNode] = []
        self.mesh: Optional[int] = None


class GLTFBuilder:
    def __init__(self):
        self.gltf = gltf.GLTF()
        self.indent = ' ' * 2
        self.mesh_stores: List[MeshStore] = []
        self.nodes: List[GLTFBuilderNode] = []
        self.root_nodes: List[GLTFBuilderNode] = []

    def export_objects(self, objects: List[bpy.types.Object]):
        for o in objects:
            root_node = self.export_object(o)
            self.root_nodes.append(root_node)

    def export_object(self, o: bpy.types.Object, indent: str='')->GLTFBuilderNode:

        node = GLTFBuilderNode(len(self.nodes), o.name)
        self.nodes.append(node)

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
            mesh_index = self.export_mesh(mesh)
            node.mesh = mesh_index

        for child in o.children:
            child_node = self.export_object(child, indent+self.indent)
            node.children.append(child_node)

        return node

    def export_mesh(self, mesh: bpy.types.Mesh)->int:

        def get_texture_layer(layers):
            for l in layers:
                if l.active:
                    return l

        mesh.update(calc_tessface=True)
        uv_texture_faces = get_texture_layer(mesh.tessface_uv_textures)
        store = MeshStore(mesh.name, mesh.vertices, mesh.materials)
        for i, face in enumerate(mesh.tessfaces):
            submesh = store.get_or_create_submesh(face.material_index)
            for triangle in store.add_face(face, uv_texture_faces.data[i]):
                for fv in triangle:
                    submesh.indices.append(fv)
            #if uv_texture_faces:
            #    store.add_face(face, uv_texture_faces.data[i])

        index = len(self.mesh_stores)
        self.mesh_stores.append(store)
        return index

    def write_to(self, gltf_path: pathlib.Path):
        # create buffer
        buffer = BufferManager()

        # material
        material_store = MaterialStore()


        meshes: List[gltf.GLTFMesh] = []
        for store in self.mesh_stores:

            mesh = store.freeze()

            is_first = True
            primitives: List[gltf.GLTFMeshPrimitive] = []
            for submesh in mesh.submeshes:
                if is_first:
                    # attributes
                    attributes = {
                        'POSITION': buffer.push_bytes(memoryview(mesh.positions.values), mesh.positions.min, mesh.positions.max),
                        'NORMAL': buffer.push_bytes(memoryview(mesh.normals.values), mesh.normals.min, mesh.normals.max)
                    }
                    is_first = False
                    if mesh.uvs:
                        attributes['TEXCOORD_0'] = buffer.push_bytes(
                            memoryview(mesh.uvs.values), mesh.uvs.min, mesh.uvs.max)

                # submesh indices
                indices_accessor_index = buffer.push_bytes(
                    memoryview(submesh.indices), None, None)

                material = mesh.materials[submesh.material_index]
                gltf_material_index = material_store.get_material_index(
                    material, buffer)

                primitives.append(gltf.GLTFMeshPrimitive(
                    attributes=attributes,
                    indices=indices_accessor_index,
                    material=gltf_material_index,
                    mode=gltf.GLTFMeshPrimitiveTopology.TRIANGLES,
                    targets=[]
                ))

            #print(position_accessor_index, indices_accessor_index)
            gltf_mesh = gltf.GLTFMesh(
                name=mesh.name,
                primitives=primitives
            )
            meshes.append(gltf_mesh)

        def to_gltf_node(node: GLTFBuilderNode):
            return gltf.GLTFNode(
                name=node.name,
                children=[child.index for child in node.children],
                mesh=node.mesh
            )

        scene = gltf.GLTFScene(
            name='scene',
            nodes=[node.index for node in self.root_nodes]
        )

        bin_path = gltf_path.parent / (gltf_path.stem + ".bin")
        uri = bin_path.relative_to(gltf_path.parent)
        gltf_root = gltf.GLTF(
            buffers=[gltf.GLTFBUffer(str(uri), len(buffer.buffer.data))],
            bufferViews=buffer.views,
            images=material_store.images,
            samplers=material_store.samplers,
            textures=material_store.textures,
            materials=material_store.materials,
            accessors=buffer.accessors,
            meshes=meshes,
            nodes=[to_gltf_node(node) for node in self.nodes],
            scenes=[scene]
        )

        # write bin
        with bin_path.open('wb') as f:
            f.write(buffer.buffer.data)

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
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    objects = get_objects(selected_only)

    builder = GLTFBuilder()
    builder.export_objects(objects)

    builder.write_to(path)
