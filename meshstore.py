import array
import mathutils


class MeshStore:

    def __init__(self, name: str)->None:
        self.name = name
        self.positions: array.array = array.array('f')
        self.indices: array.array = array.array('I')

    def add_vertex(self, v: mathutils.Vector):
        self.positions.append(v.x)
        self.positions.append(v.y)
        self.positions.append(v.z)

    def add_triangle(self, t0: mathutils.Vector, t1: mathutils.Vector, t2: mathutils.Vector):
        index = int(len(self.positions)/3)
        self.add_vertex(t0)
        self.add_vertex(t1)
        self.add_vertex(t2)
        self.indices.append(index)
        self.indices.append(index+1)
        self.indices.append(index+2)

    def add_quadrangle(self, t0, t1, t2, t3):
        index = int(len(self.positions)/3)
        self.add_vertex(t0)
        self.add_vertex(t1)
        self.add_vertex(t2)
        self.add_vertex(t3)

        self.indices.append(index)
        self.indices.append(index+1)
        self.indices.append(index+2)

        self.indices.append(index+2)
        self.indices.append(index+3)
        self.indices.append(index)
