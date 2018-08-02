import array
import mathutils
import ctypes
from typing import Any, List, Iterable
import bpy


class Vector2(ctypes.LittleEndianStructure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
    ]


class Vector3(ctypes.LittleEndianStructure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("z", ctypes.c_float)
    ]


def Vector3_from_meshVertex(v: mathutils.Vector)->Vector3:
    return Vector3(v.x, v.z, -v.y)


def get_min_max2(list: List[Vector2]):
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


def get_min_max3(list: List[Vector3]):
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


class MeshStore:

    def __init__(self, name: str,
                 vertices: List[bpy.types.MeshVertex],
                 uv_texture_faces: bpy.types.MeshTextureFaceLayer)->None:
        self.name = name
        self.positions: Any = (Vector3 * len(vertices))()
        self.normals: Any = (Vector3 * len(vertices))()
        for i, v in enumerate(vertices):
            self.positions[i] = Vector3_from_meshVertex(v.co)
            self.normals[i] = Vector3_from_meshVertex(v.normal)

        if uv_texture_faces:
            self.uvs: Any = (Vector2 * len(vertices))()

        self.indices: Any = array.array('I')

    def calc_min_max(self):
        self.position_min, self.position_max = get_min_max3(self.positions)
        self.normal_min, self.normal_max = get_min_max3(self.normals)
        if self.uvs:
            self.uvs_min, self.uvs_max = get_min_max2(self.uvs)

    def add_face(self, face: bpy.types.MeshTessFace, uv_texture_face: bpy.types.MeshTextureFace):
        if len(face.vertices) == 3:
            # triangle
            self.indices.append(face.vertices[0])
            self.indices.append(face.vertices[1])
            self.indices.append(face.vertices[2])
            if uv_texture_face:
                self.uvs[face.vertices[0]] = Vector2(
                    uv_texture_face.uv1.x, uv_texture_face.uv1.y)
                self.uvs[face.vertices[1]] = Vector2(
                    uv_texture_face.uv2.x, uv_texture_face.uv2.y)
                self.uvs[face.vertices[2]] = Vector2(
                    uv_texture_face.uv3.x, uv_texture_face.uv3.y)

        elif len(face.vertices) == 4:
            # quad
            self.indices.append(face.vertices[0])
            self.indices.append(face.vertices[1])
            self.indices.append(face.vertices[2])
            if uv_texture_face:
                pass

            self.indices.append(face.vertices[2])
            self.indices.append(face.vertices[3])
            self.indices.append(face.vertices[0])
            if uv_texture_face:
                pass

        else:
            raise Exception(f'face.vertices: {len(face.vertices)}')
