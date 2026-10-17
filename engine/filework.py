import json
import os
from datetime import datetime

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


class TextureData(tuple):
    name = None


def path(*parts):
    return os.path.join(ROOT, *parts)


def asset_path(*parts):
    return path("assets", *parts)


def read_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def write_json(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def load_settings():
    return read_json(path("settings.json"))


def load_texture(name):
    file_path = asset_path("textures", f"{name}.texture")
    if not os.path.exists(file_path):
        data = TextureData(([], {}))
        data.name = None
        return data

    with open(file_path, "r", encoding="utf-8") as file:
        lines = [line.rstrip() for line in file if line.strip()]

    texture_lines = []
    palette = {}
    for line in lines:
        if "=" in line:
            key, expr = line.split("=", 1)
            palette[key.strip()] = expr.strip()
        else:
            texture_lines.append(line)

    data = TextureData((texture_lines, palette))
    data.name = name
    return data


def load_icon(name):
    file_path = asset_path("icons", f"{name}.icon")
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.read().splitlines()
    except FileNotFoundError:
        return None

    grid = lines[:10]
    color_map = {}
    for line in lines[10:]:
        if "=" in line:
            key, value = line.split("=")
            color_map[key.strip()] = tuple(map(int, value.strip("()").split(",")))

    pixels = []
    for y in range(10):
        pixels.append([color_map.get(grid[y][x], (255, 255, 255)) for x in range(10)])
    return pixels


def save_screenshot(surface):
    import pygame
    folder = path("screenshots")
    os.makedirs(folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_path = os.path.join(folder, f"world_{timestamp}.png")
    pygame.image.save(surface, file_path)
    return file_path
