from typing import NamedTuple, List, Dict, Tuple, Optional, Any
from enum import Enum, auto
from collections import namedtuple
import json


class GLTFEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Enum):
            return o.value
        else:
            return json.JSONEncoder.default(self, o)


def recursive_asdict(o):
    if isinstance(o, tuple) and hasattr(o, '_asdict'):
        obj = {}
        for k, v in o._asdict().items():
            if v is None:
                # skip
                continue
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


class MimeType(Enum):
    Jpeg = "image/jpeg"
    Png = "image/png"


class GLTFImage(NamedTuple):
    name: str
    uri: Optional[str]
    mimeType: MimeType
    bufferView: int


class MagFilterType(Enum):
    NEAREST = 9728
    LINEAR = 9729


class MinFilterType(Enum):
    NEAREST = 9728
    LINEAR = 9729
    NEAREST_MIPMAP_NEAREST = 9984
    LINEAR_MIPMAP_NEAREST = 9985
    NEAREST_MIPMAP_LINEAR = 9986
    LINEAR_MIPMAP_LINEAR = 9987


class WrapMode(Enum):
    REPEAT = 10497
    CLAMP_TO_EDGE = 33071
    MIRRORED_REPEAT = 33648


class GLTFSampler(NamedTuple):
    magFilter: MagFilterType
    minFilter: MinFilterType
    wrapS: WrapMode
    wrapT: WrapMode


class GLTFTexture(NamedTuple):
    name: str
    sampler: int
    source: int


class GLTFMaterialPBRMetallicRoughness(NamedTuple):
    baseColorFactor: Tuple[float, float, float, float] = (0.5, 0.5, 0.5, 1.0)
    baseColorTexture: Any = None
    metallicFactor: float = 0
    roughnessFactor: float = 0.9
    metallicRoughnessTexture: Any = None


class TextureInfo(NamedTuple):
    index: int  # type: ignore
    texCoord: int


class GLTFMaterialNormalTextureInfo(NamedTuple):
    index: int  # type: ignore
    texCoord: int
    scale: float


class GLTFMaterialOcclusionTextureInfo(NamedTuple):
    index: int  # type: ignore
    texCoord: int
    strength: float


class AlphaMode(Enum):
    OPAQUE = "OPAQUE"
    MASK = "MASK"
    BLEND = "BLEND"


class GLTFMaterial(NamedTuple):
    name: str
    pbrMetallicRoughness: GLTFMaterialPBRMetallicRoughness
    normalTexture: Optional[GLTFMaterialNormalTextureInfo] = None
    occlusionTexture: Optional[GLTFMaterialOcclusionTextureInfo] = None
    emissiveTexture: Optional[TextureInfo] = None
    emissiveFactor: Tuple[float, float, float] = (0, 0, 0)
    alphaMode: AlphaMode = AlphaMode.OPAQUE
    alphaCutoff: Optional[float] = None  # for AlphaMode.MASK
    doubleSided: bool = False


def create_default_material()->GLTFMaterial:
    return GLTFMaterial(
        name="default",
        pbrMetallicRoughness=GLTFMaterialPBRMetallicRoughness()
    )


class GLTFBUffer(NamedTuple):
    uri: Optional[str] # None for glb chunk reference
    byteLength: int


class GLTFBufferView(NamedTuple):
    name: str
    buffer: Optional[int]
    byteOffset: int
    byteLength: int
    #byteStride: int
    # target:


class GLTFAccessorComponentType(Enum):
    BYTE = 5120
    UNSIGNED_BYTE = 5121
    SHORT = 5122
    UNSIGNED_SHORT = 5123
    UNSIGNED_INT = 5125
    FLOAT = 5126


def format_to_componentType(t: str)->Tuple[GLTFAccessorComponentType, int]:
    if t == 'f':
        return GLTFAccessorComponentType.FLOAT, 1
    elif t == 'I':
        return GLTFAccessorComponentType.UNSIGNED_INT, 1
    elif t == 'T{<f:x:<f:y:<f:z:}':
        return GLTFAccessorComponentType.FLOAT, 3
    elif t == 'T{<f:x:<f:y:}':
        return GLTFAccessorComponentType.FLOAT, 2
    elif t == 'T{<f:_11:<f:_12:<f:_13:<f:_14:<f:_21:<f:_22:<f:_23:<f:_24:<f:_31:<f:_32:<f:_33:<f:_34:<f:_41:<f:_42:<f:_43:<f:_44:}':
        return GLTFAccessorComponentType.FLOAT, 16
    elif t == 'T{<H:x:<H:y:<H:z:<H:w:}':
        return GLTFAccessorComponentType.UNSIGNED_SHORT, 4
    elif t == 'T{<f:x:<f:y:<f:z:<f:w:}':
        return GLTFAccessorComponentType.FLOAT, 4
    else:
        raise NotImplementedError()


class GLTFAccessorType(Enum):
    SCALAR = "SCALAR"
    VEC2 = "VEC2"
    VEC3 = "VEC3"
    VEC4 = "VEC4"
    MAT2 = "MAT2"
    MAT3 = "MAT3"
    MAT4 = "MAT4"


def accessortype_from_elementCount(count: int)->GLTFAccessorType:
    if count == 1:
        return GLTFAccessorType.SCALAR
    elif count == 2:
        return GLTFAccessorType.VEC2
    elif count == 3:
        return GLTFAccessorType.VEC3
    elif count == 4:
        return GLTFAccessorType.VEC4
    elif count == 9:
        return GLTFAccessorType.MAT3
    elif count == 16:
        return GLTFAccessorType.MAT4
    else:
        raise NotImplementedError()


class GLTFAccessor(NamedTuple):
    name: str
    bufferView: int
    byteOffset: int
    componentType: GLTFAccessorComponentType
    type: GLTFAccessorType
    count: int  # type: ignore
    min: Optional[List[float]]
    max: Optional[List[float]]


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
    indices: Optional[int]
    material: Optional[int]
    mode: GLTFMeshPrimitiveTopology
    targets: List[Dict[str, int]]


class GLTFMesh(NamedTuple):
    name: str
    primitives: List[GLTFMeshPrimitive]
    weights: List[int] = []


class GLTFNode(NamedTuple):
    name: str
    mesh: Optional[int] = None
    children: List[int] = []
    translation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    skin: Optional[int] = None


class GLTFScene(NamedTuple):
    name: str
    nodes: List[int] = []


class GLTFSkin(NamedTuple):
    name: str
    inverseBindMatrices: int
    skeleton: int
    joints: List[int]


class GLTF(NamedTuple):
    extensionsUsed: List[str] = []
    asset: GLTFAsset = GLTFAsset()
    buffers: List[GLTFBUffer] = []
    bufferViews: List[GLTFBufferView] = []
    images: List[GLTFImage] = []
    samplers: List[GLTFSampler] = []
    textures: List[GLTFTexture] = []
    materials: List[GLTFMaterial] = []
    accessors: List[GLTFAccessor] = []
    meshes: List[GLTFMesh] = []
    nodes: List[GLTFNode] = []
    scenes: List[GLTFScene] = []
    skins: List[GLTFSkin] = []

    def to_json(self):
        return json.dumps(recursive_asdict(self), cls=GLTFEncoder, indent=2)
