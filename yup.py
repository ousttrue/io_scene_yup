import bpy
import mathutils
import array
import io
import pathlib
import ctypes
from typing import List, NamedTuple, Optional, Dict, Iterable, Any
from . import gltf
from .binarybuffer import BinaryBuffer
from .meshstore import MeshStore, Vector3_from_meshVertex
from .buffermanager import BufferManager
from .materialstore import MaterialStore


class Matrix4(ctypes.LittleEndianStructure):
    _fields_ = [
        ("_11", ctypes.c_float),
        ("_12", ctypes.c_float),
        ("_13", ctypes.c_float),
        ("_14", ctypes.c_float),
        ("_21", ctypes.c_float),
        ("_22", ctypes.c_float),
        ("_23", ctypes.c_float),
        ("_24", ctypes.c_float),
        ("_31", ctypes.c_float),
        ("_32", ctypes.c_float),
        ("_33", ctypes.c_float),
        ("_34", ctypes.c_float),
        ("_41", ctypes.c_float),
        ("_42", ctypes.c_float),
        ("_43", ctypes.c_float),
        ("_44", ctypes.c_float),
    ]

    @staticmethod
    def identity()->Any:
        return Matrix4(1.0, 0.0, 0.0, 0.0,
                       0.0, 1.0, 0.0, 0.0,
                       0.0, 0.0, 1.0, 0.0,
                       0.0, 0.0, 0.0, 1.0)


class Node:
    def __init__(self, name: str, position: mathutils.Vector)->None:
        self.name = name
        self.position = Vector3_from_meshVertex(position)
        self.children: List[Node] = []
        self.mesh: Optional[MeshStore] = None
        self.skin: Optional[Skin] = None

    def __str__(self)->str:
        return f'<{self.name}>'

    def traverse(self)->Iterable[Any]:
        yield self

        for child in self.children:
            for x in child.traverse():
                yield x


class Skin:
    def __init__(self, root: Node, o: bpy.types.Object)->None:
        self.root = root
        self.object = o


class GLTFBuilder:
    def __init__(self):
        self.gltf = gltf.GLTF()
        self.indent = ' ' * 2
        self.mesh_stores: List[MeshStore] = []
        self.nodes: List[Node] = []
        self.root_nodes: List[Node] = []
        self.skins: List[Skin] = []

    def export_bone(self, matrix_world: mathutils.Matrix, bone: bpy.types.Bone)->Node:
        node = Node(bone.name, bone.head_local)
        self.nodes.append(node)

        for child in bone.children:
            child_node = self.export_bone(matrix_world, child)
            node.children.append(child_node)

        return node

    def get_or_create_skin(self, node: Node, armature_object: bpy.types.Object)->Skin:
        for skin in self.skins:
            if skin.object == armature_object:
                return skin

        skin = Skin(node, armature_object)
        self.skins.append(skin)

        armature = armature_object.data
        for b in armature.bones:
            if not b.parent:
                root_bone = self.export_bone(armature_object.matrix_world, b)
                node.children.append(root_bone)

        return skin

    def export_objects(self, objects: List[bpy.types.Object]):
        for o in objects:
            root_node = self.export_object(o)
            self.root_nodes.append(root_node)

    def export_object(self, o: bpy.types.Object, indent: str='')->Node:
        node = Node(o.name, o.matrix_world.to_translation())
        self.nodes.append(node)

        # only mesh
        if o.type == 'MESH':

            # copy
            new_obj = o.copy()
            new_obj.data = o.data.copy()
            bpy.data.scenes[0].objects.link(new_obj)

            mesh = new_obj.data

            # apply modifiers
            for m in new_obj.modifiers:
                if m.type == 'ARMATURE':
                    # skin
                    node.skin = self.get_or_create_skin(node, m.object)

            # export
            node.mesh = self.export_mesh(mesh)

        elif o.type == 'ARMATURE':
            skin = self.get_or_create_skin(node, o)

        for child in o.children:
            child_node = self.export_object(child, indent+self.indent)
            node.children.append(child_node)

        return node

    def export_mesh(self, mesh: bpy.types.Mesh)->MeshStore:

        def get_texture_layer(layers):
            for l in layers:
                if l.active:
                    return l

        mesh.update(calc_tessface=True)
        uv_texture_faces = get_texture_layer(mesh.tessface_uv_textures)
        store = MeshStore(mesh.name, mesh.vertices, mesh.materials)
        for i, face in enumerate(mesh.tessfaces):
            submesh = store.get_or_create_submesh(face.material_index)
            for triangle in store.add_face(face, uv_texture_faces.data[i] if uv_texture_faces else None):
                for fv in triangle:
                    submesh.indices.append(fv)

        self.mesh_stores.append(store)
        return store

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
                    memoryview(submesh.indices))

                try:
                    material = mesh.materials[submesh.material_index]
                except IndexError:
                    material = None

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

        def to_gltf_node(node: Node):
            return gltf.GLTFNode(
                name=node.name,
                children=[self.nodes.index(child) for child in node.children],
                translation=(node.position.x,
                             node.position.y, node.position.z),
                mesh=self.mesh_stores.index(node.mesh) if node.mesh else None,
                skin=self.skins.index(node.skin) if node.skin else None
            )

        def to_gltf_skin(skin: Skin):
            joints = [joint for joint in skin.root.traverse()]

            matrices = (Matrix4 * len(joints))()
            for i, _ in enumerate(joints):
                matrices[i] = Matrix4.identity()
            matrix_index = buffer.push_bytes(
                memoryview(matrices))  # type: ignore

            return gltf.GLTFSkin(
                inverseBindMatrices=matrix_index,
                skeleton=self.nodes.index(skin.root),
                joints=[self.nodes.index(joint) for joint in joints]
            )

        scene = gltf.GLTFScene(
            name='scene',
            nodes=[self.nodes.index(node) for node in self.root_nodes]
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
            scenes=[scene],
            skins=[to_gltf_skin(skin) for skin in self.skins]
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
