import pathlib
import ctypes
from typing import Tuple, List, Optional

from . import gltf
from .buffermanager import BufferManager
from .materialstore import MaterialStore
from .gltfbuilder import GLTFBuilder, Node, Skin, Any
from .meshstore import Mesh


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


def to_mesh(mesh: Mesh, buffer: BufferManager, material_store: MaterialStore)->gltf.GLTFMesh:
    primitives: List[gltf.GLTFMeshPrimitive] = []
    for i, submesh in enumerate(mesh.submeshes):
        if i == 0:
            # attributes
            attributes = {
                'POSITION': buffer.push_bytes(f'{mesh.name}.POSITION',
                                              memoryview(mesh.positions.values), mesh.positions.min, mesh.positions.max),
                'NORMAL': buffer.push_bytes(f'{mesh.name}.NORMAL',
                                            memoryview(mesh.normals.values), mesh.normals.min, mesh.normals.max)
            }
            if len(mesh.vertex_groups) > 0:
                # bone weights
                BoneWeights = mesh.calc_bone_weights()
                attributes['JOINTS_0'] = buffer.push_bytes(f'{mesh.name}.JOINTS_0',
                                                           BoneWeights.joints0)
                attributes['WEIGHTS_0'] = buffer.push_bytes(f'{mesh.name}.WEIGHTS_0',
                                                            BoneWeights.weights0)

            if mesh.uvs:
                attributes['TEXCOORD_0'] = buffer.push_bytes(f'{mesh.name}.TEXCOORD_0',
                                                             memoryview(mesh.uvs.values), mesh.uvs.min, mesh.uvs.max)

        # submesh indices
        indices_accessor_index = buffer.push_bytes(f'{mesh.name}.INDICES',
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
    return gltf.GLTFMesh(
        name=mesh.name,
        primitives=primitives
    )


def to_gltf(self, gltf_path: pathlib.Path, bin_path: Optional[pathlib.Path])->Tuple[gltf.GLTF, bytearray]:
    # create buffer
    buffer = BufferManager()

    # material
    material_store = MaterialStore()

    meshes: List[gltf.GLTFMesh] = [to_mesh(store.freeze(), buffer, material_store)
                                   for store in self.mesh_stores]

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
        matrix_index = buffer.push_bytes(f'{skin.root.name}.inverseBindMatrices',
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

    nodes = [to_gltf_node(node) for node in self.nodes]
    skins = [to_gltf_skin(skin) for skin in self.skins]

    uri: Optional[str] = str(bin_path.relative_to(
        gltf_path.parent)) if bin_path else None
    gltf_root = gltf.GLTF(
        buffers=[gltf.GLTFBUffer(uri, len(buffer.buffer.data))],
        bufferViews=buffer.views,
        images=material_store.images,
        samplers=material_store.samplers,
        textures=material_store.textures,
        materials=material_store.materials,
        accessors=buffer.accessors,
        meshes=meshes,
        nodes=nodes,
        scenes=[scene],
        skins=skins
    )

    return gltf_root, buffer.buffer.data
