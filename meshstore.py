import array
import mathutils
import ctypes
from typing import Any, List


class Vector3(ctypes.LittleEndianStructure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("z", ctypes.c_float)
    ]


class MeshStore:

    def __init__(self, name: str, vertices: List[mathutils.Vector])->None:
        self.name = name
        self.positions: Any = (Vector3 * len(vertices))()
        for i, pos in enumerate(vertices):
            #self.positions[i] = Vector3(pos.x, pos.y, pos.z)
            self.positions[i] = Vector3(pos.x, pos.z, -pos.y)
        self.indices: array.array = array.array('I')
        # min max
        self.min: List[float] = [float('inf')] * 3 
        self.max: List[float] = [float('-inf')] * 3
        for v in self.positions:
            if v.x < self.min[0]: self.min[0] = v.x
            if v.x > self.max[0]: self.max[0] = v.x
            if v.y < self.min[1]: self.min[1] = v.y
            if v.y > self.max[1]: self.max[1] = v.y
            if v.z < self.min[2]: self.min[2] = v.z
            if v.z > self.max[2]: self.max[2] = v.z

    def add_triangle(self, i0: int, i1: int, i2: int):
        self.indices.append(i0)
        self.indices.append(i1)
        self.indices.append(i2)
