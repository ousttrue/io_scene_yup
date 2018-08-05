from typing import Optional, List
from . import gltf
from .binarybuffer import BinaryBuffer


class BufferManager:
    def __init__(self):
        self.views: List[gltf.GLTFBufferView] = []
        self.accessors: List[gltf.GLTFAccessor] = []
        self.buffer = BinaryBuffer(0)

    def add_view(self, name: str, data: bytes)->int:
        view_index = len(self.views)
        view = self.buffer.add_values(name, data)
        self.views.append(view)
        return view_index

    def push_bytes(self, name: str,
                   values: memoryview,
                   min: Optional[List[float]]=None,
                   max: Optional[List[float]]=None)->int:
        componentType, element_count = gltf.format_to_componentType(
            values.format)
        # append view
        view_index = self.add_view(name, values.tobytes())

        # append accessor
        accessor_index = len(self.accessors)
        accessor = gltf.GLTFAccessor(
            name=name,
            bufferView=view_index,
            byteOffset=0,
            componentType=componentType,
            type=gltf.accessortype_from_elementCount(element_count),
            count=len(values),
            min=min,
            max=max
        )
        self.accessors.append(accessor)
        return accessor_index
