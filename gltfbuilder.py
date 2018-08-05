from typing import List, Optional, Iterable, Any
# blender
import bpy
import mathutils

from .meshstore import MeshStore, Vector3_from_meshVertex
from . import gltf


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
            bone_names = [
                b.name for b in node.skin.object.data.bones] if node.skin else []
            node.mesh = self.export_mesh(mesh, o.vertex_groups, bone_names)

        elif o.type == 'ARMATURE':
            skin = self.get_or_create_skin(node, o)

        for child in o.children:
            child_node = self.export_object(child, indent+self.indent)
            node.children.append(child_node)

        return node

    def export_mesh(self, mesh: bpy.types.Mesh, vertex_groups: List[bpy.types.VertexGroup], bone_names: List[str])->MeshStore:

        def get_texture_layer(layers):
            for l in layers:
                if l.active:
                    return l

        mesh.update(calc_tessface=True)
        uv_texture_faces = get_texture_layer(mesh.tessface_uv_textures)
        store = MeshStore(mesh.name, mesh.vertices,
                          mesh.materials, vertex_groups, bone_names)
        for i, face in enumerate(mesh.tessfaces):
            submesh = store.get_or_create_submesh(face.material_index)
            for triangle in store.add_face(face, uv_texture_faces.data[i] if uv_texture_faces else None):
                for fv in triangle:
                    submesh.indices.append(fv)

        self.mesh_stores.append(store)
        return store

    def get_skin_for_store(self, store: MeshStore)->Optional[Skin]:
        for node in self.nodes:
            if node.mesh == store:
                return node.skin
        return None
