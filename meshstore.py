import array
import mathutils
import ctypes
from typing import Any, List, Iterable
import bpy


class Vector3(ctypes.LittleEndianStructure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("z", ctypes.c_float)
    ]


def Vector3_from_meshVertex(v: mathutils.Vector)->Vector3:
    return Vector3(v.x, v.z, -v.y)


def get_min_max(list: List[Vector3]):
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


class MeshStore:

    def __init__(self, name: str, vertices: List[bpy.types.MeshVertex])->None:
        self.name = name
        self.positions: Any = (Vector3 * len(vertices))()
        self.normals: Any = (Vector3 * len(vertices))()
        for i, v in enumerate(vertices):
            self.positions[i] = Vector3_from_meshVertex(v.co)
            self.normals[i] = Vector3_from_meshVertex(v.normal)
        self.indices: Any = array.array('I')
        # min max
        self.position_min, self.position_max = get_min_max(self.positions)
        self.normal_min, self.normal_max = get_min_max(self.normals)


    def add_triangle(self, i0: int, i1: int, i2: int):
        self.indices.append(i0)
        self.indices.append(i1)
        self.indices.append(i2)
