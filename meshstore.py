import array
import mathutils
import ctypes
from typing import Any, List, Iterable, Dict, Generator, Tuple, Optional, NamedTuple
import bpy


class Vector2(ctypes.LittleEndianStructure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
    ]


def Vector2_from_faceUV(uv: mathutils.Vector)->Vector2:
    return Vector2(uv.x, -uv.y)


class Vector3(ctypes.LittleEndianStructure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("z", ctypes.c_float)
    ]

    def __sub__(self, rhs):
        return Vector3(self.x-rhs.x, self.y-rhs.y, self.z-rhs.z)


def Vector3_from_meshVertex(v: mathutils.Vector)->Vector3:
    return Vector3(v.x, v.z, -v.y)


def get_min_max2(list: Iterable[Vector2]):
    min: List[float] = [float('inf')] * 2
    max: List[float] = [float('-inf')] * 2
    for v in list:
        if v.x < min[0]:
            min[0] = v.x
        if v.x > max[0]:
            max[0] = v.x
        if v.y < min[1]:
            min[1] = v.y
        if v.y > max[1]:
            max[1] = v.y
    return min, max


def get_min_max3(list: Iterable[Vector3]):
    min: List[float] = [float('inf')] * 3
    max: List[float] = [float('-inf')] * 3
    for v in list:
        if v.x < min[0]:
            min[0] = v.x
        if v.x > max[0]:
            max[0] = v.x
        if v.y < min[1]:
            min[1] = v.y
        if v.y > max[1]:
            max[1] = v.y
        if v.z < min[2]:
            min[2] = v.z
        if v.z > max[2]:
            max[2] = v.z
    return min, max


def getFaceUV(mesh, i, faces, count=3):
    active_uv_texture = None
    for t in mesh.tessface_uv_textures:
        if t.active:
            active_uv_texture = t
            break
    if active_uv_texture and active_uv_texture.data[i]:
        uvFace = active_uv_texture.data[i]
        if count == 3:
            return (uvFace.uv1, uvFace.uv2, uvFace.uv3)
        elif count == 4:
            return (uvFace.uv1, uvFace.uv2, uvFace.uv3, uvFace.uv4)
        else:
            print(count)
            assert(False)
    else:
        return ((0, 0), (0, 0), (0, 0), (0, 0))


class Submesh:
    def __init__(self, material_index: int)->None:
        self.indices: Any = array.array('I')
        self.material_index = material_index


class Values(NamedTuple):
    values: memoryview
    min: List[float]
    max: List[float]


class Vector4(ctypes.LittleEndianStructure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("z", ctypes.c_float),
        ("w", ctypes.c_float)
    ]


class IVector4(ctypes.LittleEndianStructure):
    _fields_ = [
        ("x", ctypes.c_ushort),
        ("y", ctypes.c_ushort),
        ("z", ctypes.c_ushort),
        ("w", ctypes.c_ushort)
    ]


class BoneWeight(ctypes.LittleEndianStructure):
    _fields_ = [
        ("i0", ctypes.c_int),
        ("i1", ctypes.c_int),
        ("i2", ctypes.c_int),
        ("i3", ctypes.c_int),
        ("weights", Vector4),
    ]


def PushBoneWeight(self: BoneWeight, i: int, w: float):
    if self.weights.x == 0:
        self.i0 = i
        self.weights.x = w
    elif self.weights.y == 0:
        self.i1 = i
        self.weights.y = w
    elif self.weights.z == 0:
        self.i2 = i
        self.weights.z = w
    elif self.weights.w == 0:
        self.i3 = i
        self.weights.w = w
    else:
        raise NotImplementedError()


def GetBoneJoints(self: BoneWeight, group_index_to_joint_index: Dict[int, int]):
    return IVector4(
        group_index_to_joint_index[self.i0],
        group_index_to_joint_index[self.i1],
        group_index_to_joint_index[self.i2],
        group_index_to_joint_index[self.i3]
    )


class Mesh(NamedTuple):
    name: str
    positions: Values
    normals: Values
    uvs: Optional[Values]
    materials: List[bpy.types.Material]
    submeshes: List[Submesh]
    joints: Optional[memoryview]
    weights: Optional[memoryview]


class FaceVertex(NamedTuple):
    position_index: int
    normal: Optional[Vector3]
    uv: Optional[Vector2]

    def __hash__(self):
        return hash(self.position_index)


class MeshStore:

    def __init__(self, name: str,
                 vertices: List[bpy.types.MeshVertex],
                 materials: List[bpy.types.Material],
                 vertex_groups: List[bpy.types.VertexGroup],
                 bone_names: List[str]
                 )->None:
        self.name = name
        self.positions: Any = (Vector3 * len(vertices))()
        self.normals: Any = (Vector3 * len(vertices))()
        for i, v in enumerate(vertices):
            self.positions[i] = Vector3_from_meshVertex(v.co)
            self.normals[i] = Vector3_from_meshVertex(v.normal)

        self.submesh_map: Dict[int, Submesh] = {}

        self.materials: List[bpy.types.Material] = materials

        self.face_vertices: List[FaceVertex] = []
        self.face_vertex_map: Dict[FaceVertex, int] = {}

        self.vertex_group_names = [g.name for g in vertex_groups]
        self.bone_names = bone_names
        self.bone_weights = (BoneWeight * len(vertices))()
        for i, v in enumerate(vertices):
            for ve in v.groups:
                vg_name = self.vertex_group_names[ve.group]
                if vg_name in self.bone_names:
                    PushBoneWeight(self.bone_weights[i], ve.group, ve.weight)

    def get_or_create_submesh(self, material_index: int)->Submesh:
        if material_index not in self.submesh_map:
            self.submesh_map[material_index] = Submesh(material_index)
        return self.submesh_map[material_index]

    def get_or_add_face(self, vertex_index: int, uv: mathutils.Vector, normal: Optional[mathutils.Vector])->int:
        face = FaceVertex(vertex_index,
                          Vector3_from_meshVertex(normal) if normal else None,
                          Vector2_from_faceUV(uv) if uv else None)
        if face not in self.face_vertex_map:
            index = len(self.face_vertices)
            self.face_vertex_map[face] = index
            self.face_vertices.append(face)
        return self.face_vertex_map[face]

    def add_face(self, face: bpy.types.MeshTessFace, uv_texture_face: Optional[bpy.types.MeshTextureFace])->List[Tuple[int, int, int]]:

        if len(face.vertices) == 3:
            i0 = self.get_or_add_face(
                face.vertices[0],
                uv_texture_face.uv1 if uv_texture_face else None,
                None if face.use_smooth else face.normal)

            i1 = self.get_or_add_face(
                face.vertices[1],
                uv_texture_face.uv2 if uv_texture_face else None,
                None if face.use_smooth else face.normal)

            i2 = self.get_or_add_face(
                face.vertices[2],
                uv_texture_face.uv3 if uv_texture_face else None,
                None if face.use_smooth else face.normal)
            return [(i0, i1, i2)]

        elif len(face.vertices) == 4:
            i0 = self.get_or_add_face(
                face.vertices[0],
                uv_texture_face.uv1 if uv_texture_face else None,
                None if face.use_smooth else face.normal)

            i1 = self.get_or_add_face(
                face.vertices[1],
                uv_texture_face.uv2 if uv_texture_face else None,
                None if face.use_smooth else face.normal)

            i2 = self.get_or_add_face(
                face.vertices[2],
                uv_texture_face.uv3 if uv_texture_face else None,
                None if face.use_smooth else face.normal)

            i3 = self.get_or_add_face(
                face.vertices[3],
                uv_texture_face.uv4 if uv_texture_face else None,
                None if face.use_smooth else face.normal)

            return [(i0, i1, i2), (i2, i3, i0)]

        else:
            raise Exception(f'face.vertices: {len(face.vertices)}')

    def freeze(self, skin_bone_names: List[str])->Mesh:

        positions = (Vector3 * len(self.face_vertices))()
        fv_to_v_index: Dict[int, int] = {}
        for i, v in enumerate(self.face_vertices):
            positions[i] = self.positions[v.position_index]
            fv_to_v_index[i] = v.position_index
        position_min, position_max = get_min_max3(positions)

        normals = (Vector3 * len(self.face_vertices))()
        for i, v in enumerate(self.face_vertices):
            normals[i] = v.normal if v.normal else self.normals[v.position_index]
        normal_min, normal_max = get_min_max3(normals)

        uvs_values = None
        if any(f.uv for f in self.face_vertices):
            uvs = (Vector2 * len(self.face_vertices))()
            for i, v in enumerate(self.face_vertices):
                uvs[i] = v.uv
            uvs_min, uvs_max = get_min_max2(uvs)
            uvs_values = Values(memoryview(uvs), uvs_min,  # type: ignore
                                uvs_max)

        submeshes = [x for x in self.submesh_map.values()]

        joints = None
        weights = None
        if skin_bone_names and len(skin_bone_names) > 0:
            group_index_to_joint_index = {i: skin_bone_names.index(
                vertex_group) for i, vertex_group in enumerate(self.vertex_group_names)}
            joints = (IVector4 * len(self.face_vertices))()
            weights = (Vector4 * len(self.face_vertices))()
            for i, v in enumerate(self.face_vertices):
                index = fv_to_v_index[i]
                joints[i] = GetBoneJoints(
                    self.bone_weights[index], group_index_to_joint_index)
                weights[i] = self.bone_weights[index].weights

        return Mesh(
            name=self.name,
            positions=Values(memoryview(positions), position_min,  # type: ignore
                             position_max),
            normals=Values(memoryview(normals), normal_min,  # type: ignore
                           normal_max),
            uvs=uvs_values if uvs_values else None,
            materials=self.materials,
            submeshes=submeshes,
            joints=memoryview(joints),  # type: ignore
            weights=memoryview(weights)  # type: ignore
        )
