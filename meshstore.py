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
    values: Any
    min: List[float]
    max: List[float]


class BoneWeights(NamedTuple):
    joints0: memoryview
    weights0: memoryview


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


class Mesh(NamedTuple):
    name: str
    positions: Values
    normals: Values
    uvs: Optional[Values]
    materials: List[bpy.types.Material]
    submeshes: List[Submesh]
    # bone weights
    vertex_groups: List[bpy.types.VertexGroup]
    fv_to_v_index: Dict[int, int]

    def calc_bone_weights(self)->BoneWeights:
        joints0 = (IVector4 * len(self.positions.values))()
        weights0 = (Vector4 * len(self.positions.values))()
        return BoneWeights(
            joints0=memoryview(joints0), # type: ignore
            weights0=memoryview(weights0), # type: ignore
        )


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
                 vertex_groups: List[bpy.types.VertexGroup]
                 )->None:
        self.name = name
        self.positions: Any = (Vector3 * len(vertices))()
        self.normals: Any = (Vector3 * len(vertices))()
        for i, v in enumerate(vertices):
            self.positions[i] = Vector3_from_meshVertex(v.co)
            self.normals[i] = Vector3_from_meshVertex(v.normal)

        self.submesh_map: Dict[int, Submesh] = {}

        self.materials: List[bpy.types.Material] = materials

        self.faceVertices: List[FaceVertex] = []
        self.faceVertexMap: Dict[FaceVertex, int] = {}

        self.vertex_groups = vertex_groups

    def get_or_create_submesh(self, material_index: int)->Submesh:
        if material_index not in self.submesh_map:
            self.submesh_map[material_index] = Submesh(material_index)
        return self.submesh_map[material_index]

    def get_or_add_face(self, vertex_index: int, uv: mathutils.Vector, normal: Optional[mathutils.Vector])->int:
        face = FaceVertex(vertex_index,
                          Vector3_from_meshVertex(normal) if normal else None,
                          Vector2_from_faceUV(uv) if uv else None)
        if face not in self.faceVertexMap:
            index = len(self.faceVertices)
            self.faceVertexMap[face] = index
            self.faceVertices.append(face)
        return self.faceVertexMap[face]

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

    def freeze(self)->Mesh:

        positions = (Vector3 * len(self.faceVertices))()
        fv_to_v_index: Dict[int, int] = {}
        for i, v in enumerate(self.faceVertices):
            positions[i] = self.positions[v.position_index]
            fv_to_v_index[i] = v.position_index
        position_min, position_max = get_min_max3(positions)

        normals = (Vector3 * len(self.faceVertices))()
        for i, v in enumerate(self.faceVertices):
            normals[i] = v.normal if v.normal else self.normals[v.position_index]
        normal_min, normal_max = get_min_max3(normals)

        uvs_values = None
        if any(f.uv for f in self.faceVertices):
            uvs = (Vector2 * len(self.faceVertices))()
            for i, v in enumerate(self.faceVertices):
                uvs[i] = v.uv
            uvs_min, uvs_max = get_min_max2(uvs)
            uvs_values = Values(uvs, uvs_min, uvs_max)

        submeshes = [x for x in self.submesh_map.values()]
        return Mesh(
            name=self.name,
            positions=Values(positions, position_min, position_max),
            normals=Values(normals, normal_min, normal_max),
            uvs=uvs_values if uvs_values else None,
            materials=self.materials,
            submeshes=submeshes,
            vertex_groups=self.vertex_groups,
            fv_to_v_index=fv_to_v_index
        )
