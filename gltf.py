from typing import NamedTuple, List, Dict
from enum import Enum, auto
from collections import namedtuple
import json


class ValueEnum(Enum):
    pass


class NameEnum(Enum):
    pass


class GLTFEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ValueEnum):
            return o.value
        elif isinstance(o, NameEnum):
            return o.name
        else:
            return json.JSONEncoder.default(self, o)


def recursive_asdict(o):
    if isinstance(o, tuple) and hasattr(o, '_asdict'):
        obj = {}
        for k, v in o._asdict().items():
            if isinstance(v, (list, tuple)):
                if len(v) == 0:
                    # skip empty list
                    continue
            if isinstance(v, dict):
                if len(v) == 0:
                    # skip empty list
                    continue
            obj[k] = recursive_asdict(v)
        return obj
    elif isinstance(o, (list, tuple)):
        return [recursive_asdict(x) for x in o]
    else:
        return o


class GLTFAsset(NamedTuple):
    generator: str = 'io_scene_yup'
    version: str = '2.0'


class GLTFBUffer(NamedTuple):
    uri: str
    byteLength: int


class GLTFBufferView(NamedTuple):
    buffer: int
    byteOffset: int
    byteLength: int
    #byteStride: int
    # target:


class GLTFAccessorComponentType(ValueEnum):
    BYTE = 5120
    UNSIGNED_BYTE = 5121
    SHORT = 5122
    UNSIGNED_SHORT = 5123
    UNSIGNED_INT = 5125
    FLOAT = 5126


def format_to_componentType(t: str)->GLTFAccessorComponentType:
    if t == 'f':
        return GLTFAccessorComponentType.FLOAT
    elif t == 'I':
        return GLTFAccessorComponentType.UNSIGNED_INT
    else:
        raise NotImplementedError()


class GLTFAccessorType(NameEnum):
    SCALAR = 1
    VEC2 = 2
    VEC3 = 3
    VEC4 = 4
    #MAT2 = auto()
    MAT3 = 9
    MAT4 = 16


class GLTFAccessor(NamedTuple):
    bufferView: int
    byteOffset: int
    componentType: GLTFAccessorComponentType
    type: GLTFAccessorType
    count: int


class GLTFMeshPrimitiveTopology(ValueEnum):
    POINTS = 0
    LINES = 1
    LINE_LOOP = 2
    LINE_STRIP = 3
    TRIANGLES = 4
    TRIANGLE_STRIP = 5
    TRIANGLE_FAN = 6


class GLTFMeshPrimitive(NamedTuple):
    attributes: Dict[str, int]
    indices: int
    material: int
    mode: GLTFMeshPrimitiveTopology
    targets: List[Dict[str, int]]


class GLTFMesh(NamedTuple):
    name: str
    primitives: List[GLTFMeshPrimitive]
    weights: List[int] = []


class GLTF(NamedTuple):
    extensionsUsed: List[str] = []
    asset: GLTFAsset = GLTFAsset()
    buffers: List[GLTFBUffer] = []
    bufferViews: List[GLTFBufferView] = []
    accessors: List[GLTFAccessor] = []
    meshes: List[GLTFMesh] = []

    def to_json(self):
        return json.dumps(recursive_asdict(self), cls=GLTFEncoder, indent=2)
