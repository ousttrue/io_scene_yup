import bpy
import mathutils
import array
import io
import pathlib
from typing import List, NamedTuple, Optional, Dict
from . import gltf
from .binarybuffer import BinaryBuffer
from .meshstore import MeshStore


def image_to_png(image: bpy.types.Image)->bytes:
    '''
    https://blender.stackexchange.com/questions/62072/does-blender-have-a-method-to-a-get-png-formatted-bytearray-for-an-image-via-pyt
    '''
    import struct
    import zlib

    width = image.size[0]
    height = image.size[1]
    buf = bytearray([int(p * 255) for p in image.pixels])

    # reverse the vertical line order and add null bytes at the start
    width_byte_4 = width * 4
    raw_data = b''.join(b'\x00' + buf[span:span + width_byte_4]
                        for span in range((height - 1) * width_byte_4, -1, - width_byte_4))

    def png_pack(png_tag, data):
        chunk_head = png_tag + data
        return (struct.pack("!I", len(data)) +
                chunk_head +
                struct.pack("!I", 0xFFFFFFFF & zlib.crc32(chunk_head)))

    png_bytes = b''.join([
        b'\x89PNG\r\n\x1a\n',
        png_pack(b'IHDR', struct.pack("!2I5B", width, height, 8, 6, 0, 0, 0)),
        png_pack(b'IDAT', zlib.compress(raw_data, 9)),
        png_pack(b'IEND', b'')])
    return png_bytes


class BufferManager:
    def __init__(self):
        self.views: List[gltf.GLTFBufferView] = []
        self.accessors: List[gltf.GLTFAccessor] = []
        self.buffer = BinaryBuffer(0)

    def add_view(self, data: bytes)->int:
        view_index = len(self.views)
        view = self.buffer.add_values(data)
        self.views.append(view)
        return view_index

    def push_bytes(self, values: memoryview,
                   min: Optional[List[float]], max: Optional[List[float]])->int:
        componentType, element_count = gltf.format_to_componentType(
            values.format)
        # append view
        view_index = self.add_view(values.tobytes())

        # append accessor
        accessor_index = len(self.accessors)
        accessor = gltf.GLTFAccessor(
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


class MaterialStore:
    def __init__(self):
        self.images: List[gltf.GLTFImage] = []
        self.samplers: List[gltf.GLTFSampler] = []
        self.textures: List[gltf.GLTFTexture] = []
        self.texture_map: Dict[bpy.tyeps.Image, int] = {}
        self.materials: List[gltf.GLTFMaterial] = []
        self.material_map: Dict[bpy.types.Material, int] = {}

    def get_texture_index(self, texture: bpy.types.Image, buffer: BufferManager)->int:
        if texture in self.texture_map:
            return self.texture_map[texture]

        gltf_texture_index = len(self.textures)
        self.texture_map[texture] = gltf_texture_index
        self.add_texture(texture, buffer)
        return gltf_texture_index

    def add_texture(self, src: bpy.types.Image, buffer: BufferManager):
        image_index = len(self.images)

        print(f'add_texture: {src.name}')
        png = image_to_png(src)
        view_index = buffer.add_view(png)

        self.images.append(gltf.GLTFImage(
            name=src.name,
            uri=None,
            mimeType=gltf.MimeType.Png,
            bufferView=view_index
        ))

        sampler_index = len(self.samplers)
        self.samplers.append(gltf.GLTFSampler(
            magFilter=gltf.MagFilterType.NEAREST,
            minFilter=gltf.MinFilterType.NEAREST,
            wrapS=gltf.WrapMode.REPEAT,
            wrapT=gltf.WrapMode.REPEAT
        ))

        dst = gltf.GLTFTexture(
            name=src.name,
            source=image_index,
            sampler=sampler_index
        )
        self.textures.append(dst)

    def get_material_index(self, material: bpy.types.Material, bufferManager: BufferManager)->int:
        if material in self.material_map:
            return self.material_map[material]

        gltf_material_index = len(self.materials)
        self.material_map[material] = gltf_material_index
        self.add_material(material, bufferManager)
        return gltf_material_index

    def add_material(self, src: bpy.types.Material, bufferManager: BufferManager):
        # texture
        color_texture = None
        normal_texture = None
        for i, slot in enumerate(src.texture_slots):
            if src.use_textures[i] and slot and slot.texture:
                if slot.use_map_color_diffuse and slot.texture and slot.texture.image:
                    color_texture_index = self.get_texture_index(
                        slot.texture.image, bufferManager)
                    color_texture = gltf.TextureInfo(
                        index=color_texture_index,
                        texCoord=None
                    )
                elif slot.use_map_normal and slot.texture and slot.texture.image:
                    normal_texture_index = self.get_texture_index(
                        slot.texture.image, bufferManager)
                    normal_texture=gltf.GLTFMaterialNormalTextureInfo(
                            index=normal_texture_index,
                            texCoord=None,
                            scale=slot.normal_factor,
                    )

        dst = gltf.GLTFMaterial(
            name=src.name,
            pbrMetallicRoughness=gltf.GLTFMaterialPBRMetallicRoughness(
                baseColorFactor=(1.0, 1.0, 1.0, 1.0),
                baseColorTexture=color_texture,
                metallicFactor=0,
                roughnessFactor=0.9,
                metallicRoughnessTexture=None
            ),
            normalTexture=normal_texture,
            occlusionTexture=None,
            emissiveTexture=None,
            emissiveFactor=(0, 0, 0),
            alphaMode=gltf.AlphaMode.OPAQUE,
            alphaCutoff=None,
            doubleSided=False
        )
        self.materials.append(dst)


class GLTFBuilderNode:
    def __init__(self, index: int, name: str)->None:
        self.index = index
        self.name = name
        self.children: List[GLTFBuilderNode] = []
        self.mesh: Optional[int] = None


class GLTFBuilder:
    def __init__(self):
        self.gltf = gltf.GLTF()
        self.indent = ' ' * 2
        self.meshes: List[MeshStore] = []
        self.nodes: List[GLTFBuilderNode] = []
        self.root_nodes: List[GLTFBuilderNode] = []

    def export_objects(self, objects: List[bpy.types.Object]):
        for o in objects:
            root_node = self.export_object(o)
            self.root_nodes.append(root_node)

    def export_object(self, o: bpy.types.Object, indent: str='')->GLTFBuilderNode:

        node = GLTFBuilderNode(len(self.nodes), o.name)
        self.nodes.append(node)

        # only mesh
        if o.type == 'MESH':

            # copy
            new_obj = o.copy()
            new_obj.data = o.data.copy()
            bpy.data.scenes[0].objects.link(new_obj)

            mesh = new_obj.data

            # apply modifiers exclude armature

            # rotate to Y-UP

            # export
            mesh_index = self.export_mesh(mesh)
            node.mesh = mesh_index

        for child in o.children:
            child_node = self.export_object(child, indent+self.indent)
            node.children.append(child_node)

        return node

    def export_mesh(self, mesh: bpy.types.Mesh)->int:

        def get_texture_layer(layers):
            for l in layers:
                if l.active:
                    return l

        mesh.update(calc_tessface=True)
        uv_texture_faces = get_texture_layer(mesh.tessface_uv_textures)
        store = MeshStore(mesh.name, mesh.vertices,
                          uv_texture_faces, mesh.materials)
        for i, face in enumerate(mesh.tessfaces):
            submesh = store.get_or_create_submesh(face.material_index)
            submesh.add_face(face)
            if uv_texture_faces:
                store.add_face(face, uv_texture_faces.data[i])
        store.calc_min_max()

        index = len(self.meshes)
        self.meshes.append(store)
        return index

    def write_to(self, gltf_path: pathlib.Path):
        # create buffer
        buffer = BufferManager()

        # material
        material_store = MaterialStore()

        # meshes
        meshes: List[gltf.GLTFMesh] = []
        for mesh in self.meshes:

            is_first = True
            primitives: List[gltf.GLTFMeshPrimitive] = []
            for material_index, submesh in mesh.submesh_map.items():
                if is_first:
                    # attributes
                    attributes = {
                        'POSITION': buffer.push_bytes(memoryview(mesh.positions), mesh.position_min, mesh.position_max),
                        'NORMAL': buffer.push_bytes(memoryview(mesh.normals), mesh.normal_min, mesh.normal_max)
                    }
                    is_first = False
                    if mesh.uvs:
                        attributes['TEXCOORD_0'] = buffer.push_bytes(
                            memoryview(mesh.uvs), mesh.uvs_min, mesh.uvs_max)

                # submesh indices
                indices_accessor_index = buffer.push_bytes(
                    memoryview(submesh.indices), None, None)

                material = mesh.materials[material_index]
                gltf_material_index = material_store.get_material_index(
                    material, buffer)

                primitives.append(gltf.GLTFMeshPrimitive(
                    attributes=attributes,
                    indices=indices_accessor_index,
                    material=gltf_material_index,
                    mode=gltf.GLTFMeshPrimitiveTopology.TRIANGLES,
                    targets=[]
                ))

            #print(position_accessor_index, indices_accessor_index)
            gltf_mesh = gltf.GLTFMesh(
                name=mesh.name,
                primitives=primitives
            )
            meshes.append(gltf_mesh)

        def to_gltf_node(node: GLTFBuilderNode):
            return gltf.GLTFNode(
                name=node.name,
                children=[child.index for child in node.children],
                mesh=node.mesh
            )

        scene = gltf.GLTFScene(
            name='scene',
            nodes=[node.index for node in self.root_nodes]
        )

        bin_path = gltf_path.parent / (gltf_path.stem + ".bin")
        uri = bin_path.relative_to(gltf_path.parent)
        gltf_root = gltf.GLTF(
            buffers=[gltf.GLTFBUffer(str(uri), len(buffer.buffer.data))],
            bufferViews=buffer.views,
            images=material_store.images,
            samplers=material_store.samplers,
            textures=material_store.textures,
            materials=material_store.materials,
            accessors=buffer.accessors,
            meshes=meshes,
            nodes=[to_gltf_node(node) for node in self.nodes],
            scenes=[scene]
        )

        # write bin
        with bin_path.open('wb') as f:
            f.write(buffer.buffer.data)

        # write gltf
        with gltf_path.open('wb') as f:
            f.write(gltf_root.to_json().encode('utf-8'))


def get_objects(selected_only: bool):
    if selected_only:
        return bpy.context.selected_objects
    else:
        return bpy.data.scenes[0].objects


def export(path: pathlib.Path, selected_only: bool):

    # object mode
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    objects = get_objects(selected_only)

    builder = GLTFBuilder()
    builder.export_objects(objects)

    builder.write_to(path)
