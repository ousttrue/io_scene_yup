from typing import NamedTuple, List

from collections import namedtuple
import json


def recursive_asdict(o):
    if isinstance(o, tuple) and hasattr(o, '_asdict'):
        obj = {}
        for k, v in o._asdict().items():
            if isinstance(v, (list, tuple)) and len(v)==0:
                # skip empty list
                continue
            obj[k] = recursive_asdict(v)
        return obj
    else:
        return o


class Asset(NamedTuple):
    generator: str = 'io_scene_yup'
    version: str = '2.0'


class GLTF(NamedTuple):
    extensionsUsed: List[str] = []
    asset: Asset = Asset()

    def to_json(self):
        return json.dumps(recursive_asdict(self), indent=4)
