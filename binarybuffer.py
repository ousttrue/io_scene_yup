from typing import Tuple
from . import gltf


class BinaryBuffer:
    def __init__(self, index: int)->None:
        self.index = index
        self.data = bytearray()

    def append(self, data: bytes) -> gltf.GLTFBufferView:
        offset = len(self.data)
        self.data += data
        return gltf.GLTFBufferView(
            buffer=self.index,
            byteOffset=offset,
            byteLength=len(data)
        )
