from typing import Tuple
from . import gltf


class BinaryBuffer:
    def __init__(self, index: int)->None:
        self.index = index
        self.data = bytearray()

    def add_values(self, name: str, data: bytes) -> gltf.GLTFBufferView:
        # alignment
        if len(self.data) % 4 != 0:
            padding = 4 - len(self.data) % 4
            for _ in range(padding):
                self.data.append(0)

        offset = len(self.data)
        self.data += data
        return gltf.GLTFBufferView(
            name = name,
            buffer=self.index,
            byteOffset=offset,
            byteLength=len(data)
        )
