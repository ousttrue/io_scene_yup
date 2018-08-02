import bpy
import mathutils
import array
import io
import pathlib
from typing import List, NamedTuple, Optional
from . import gltf
from .binarybuffer import BinaryBuffer
from .meshstore import MeshStore


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
        self.meshes: List[MeshStore] = []
        self.buffers: List[BinaryBuffer] = []
        self.views: List[gltf.GLTFBufferView] = []
        self.accessors: List[gltf.GLTFAccessor] = []
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
        uv_texture_faces=get_texture_layer(mesh.tessface_uv_textures)
        store = MeshStore(mesh.name, mesh.vertices, uv_texture_faces, mesh.materials)
        for i, face in enumerate(mesh.tessfaces):
            submesh = store.get_or_create_submesh(face.material_index)
            submesh.add_face(face)
            if uv_texture_faces:
                store.add_face(face, uv_texture_faces.data[i])
        store.calc_min_max()

        index = len(self.meshes)
        self.meshes.append(store)
        return index

    def add_buffer(self, path: pathlib.Path)->int:
        index = len(self.buffers)
        self.buffers.append(BinaryBuffer(index))
        return index

    def push_bytes(self, buffer_index: int, values: memoryview, 
            min: Optional[List[float]], max: Optional[List[float]])->int:
        componentType, element_count = gltf.format_to_componentType(values.format)
        # append view
        view_index = len(self.views)
        view = self.buffers[buffer_index].add_values(values.tobytes())
        self.views.append(view)

        # append accessor
        accessor_index = len(self.accessors)
        accessor = gltf.GLTFAccessor(
            bufferView=view_index,
            byteOffset=0,
            componentType=componentType,
            type=gltf.GLTFAccessorType(element_count),
            count=len(values),
            min=min,
            max=max
        )
        self.accessors.append(accessor)
        return accessor_index

    def write_to(self, gltf_path: pathlib.Path):
        # create buffer
        bin_path = gltf_path.parent / (gltf_path.stem + ".bin")
        buffer_index = self.add_buffer(bin_path)

        # meshes
        materials: List[gltf.GLTFMaterial] = []
        material_map: Dict[bpy.types.Material, int] = {}

        meshes: List[gltf.GLTFMesh] = []
        for mesh in self.meshes:

            is_first=True
            primitives: List[gltf.GLTFMeshPrimitive] = []
            for material_index, submesh in mesh.submesh_map.items():
                if is_first:
                    # attributes
                    attributes = {
                        'POSITION': self.push_bytes(
                            buffer_index, memoryview(mesh.positions), mesh.position_min, mesh.position_max),
                        'NORMAL': self.push_bytes(
                            buffer_index, memoryview(mesh.normals), mesh.normal_min, mesh.normal_max)
                    }
                    is_first=False
                    if mesh.uvs:
                        attributes['TEXCOORD_0'] = self.push_bytes(
                            buffer_index, memoryview(mesh.uvs), mesh.uvs_min, mesh.uvs_max)

                # submesh indices
                indices_accessor_index = self.push_bytes(buffer_index, memoryview(submesh.indices), None, None)

                material = mesh.materials[material_index]

                gltf_material_index=None
                if material in material_map:
                    gltf_material_index = material_map[material]
                else:
                    gltf_material_index = len(materials)
                    material_map[material] = gltf_material_index
                    materials.append(gltf.GLTFMaterial("material"))

                primitives.append(gltf.GLTFMeshPrimitive(
                        attributes=attributes,
                        indices=indices_accessor_index,
                        material=material_index,
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
            nodes = [node.index for node in self.root_nodes]
        )

        uri = bin_path.relative_to(gltf_path.parent)
        gltf_root = gltf.GLTF(
            materials=materials,
            buffers=[gltf.GLTFBUffer(str(uri), len(self.buffers[0].data))],
            bufferViews=self.views,
            accessors=self.accessors,
            meshes=meshes,
            nodes=[to_gltf_node(node) for node in self.nodes],
            scenes=[scene]
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
    if bpy.context.mode!='OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    objects = get_objects(selected_only)

    builder = GLTFBuilder()
    builder.export_objects(objects)

    builder.write_to(path)
