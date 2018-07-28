from typing import NamedTuple, List, Dict
from enum import Enum
from collections import namedtuple
import json


class GLTFEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, GLTFMeshPrimitiveTopology):
            return o.value
        else:
            return JSONEncoder.default(self, o)


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


class GLTFMeshPrimitiveTopology(Enum):
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
    meshes: List[GLTFMesh] = []

    def to_json(self):
        return json.dumps(recursive_asdict(self), cls=GLTFEncoder, indent=2)
