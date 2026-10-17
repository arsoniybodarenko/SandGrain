import inspect
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from engine import filework
from engine.materials import MATERIALS, Material

OUTPUT_DIR = filework.path("resources", "materials")
FORBIDDEN = re.compile(r'[\\/:*?"<>|]')


def to_plain(value):
    if isinstance(value, dict):
        return {str(k): to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_plain(v) for v in value]
    return value


def material_to_dict(key, material):
    data = {"id": key}
    for name in inspect.signature(Material.__init__).parameters:
        if name == "self":
            continue
        value = getattr(material, name)
        if name == "texture":
            value = getattr(value, "name", None)
        data[name] = to_plain(value)
    return data


def file_name(key):
    return FORBIDDEN.sub("_", key) + ".json"


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for old in os.listdir(OUTPUT_DIR):
        if old.endswith(".json"):
            os.remove(os.path.join(OUTPUT_DIR, old))
    for key, material in MATERIALS.items():
        filework.write_json(os.path.join(OUTPUT_DIR, file_name(key)), material_to_dict(key, material))
    print(f"Материалов записано: {len(MATERIALS)} -> {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
