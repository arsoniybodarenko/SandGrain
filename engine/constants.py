import json
import os

_PATH = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "constants.json"))

with open(_PATH, "r", encoding="utf-8") as _file:
    _data = json.load(_file)

BORDER_SIZE = _data["BORDER_SIZE"]
GAME_WIDTH = _data["GAME_WIDTH"]
GAME_HEIGHT = _data["GAME_HEIGHT"]
COLUMN_WIDTH = _data["COLUMN_WIDTH"]
PIXEL_SIZE = _data["PIXEL_SIZE"]
FPS = _data["FPS"]
PHYSICS_TPS = _data["PHYSICS_TPS"]

MENU_WIDTH = COLUMN_WIDTH * 3
WINDOW_WIDTH = GAME_WIDTH + MENU_WIDTH
WINDOW_HEIGHT = GAME_HEIGHT

painted_colors = [(name, tuple(color)) for name, color in _data["painted_colors"]]
BRUSH_SUBTOOLS = list(_data["BRUSH_SUBTOOLS"])
OBJECT_SUBTOOLS = list(_data["OBJECT_SUBTOOLS"])
TOOLS = list(_data["TOOLS"])

TOOL_SUBTYPES = {
    "Рисование": BRUSH_SUBTOOLS,
    "Объекты": OBJECT_SUBTOOLS,
    "Выбор цвета": painted_colors
}
