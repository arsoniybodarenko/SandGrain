from types import SimpleNamespace

from . import filework

__all__ = [
    "SETTINGS", "BORDER_SIZE", "GAME_WIDTH", "GAME_HEIGHT", "COLUMN_WIDTH", "PIXEL_SIZE", "FPS", "PHYSICS_TPS",
    "MENU_WIDTH", "WINDOW_WIDTH", "WINDOW_HEIGHT", "painted_colors", "BRUSH_SUBTOOLS", "OBJECT_SUBTOOLS",
    "TOOLS", "TOOL_SUBTYPES",
]


def _wrap(value):
    if isinstance(value, dict):
        return SimpleNamespace(**{key: _wrap(item) for key, item in value.items()})
    return value


RAW = filework.load_settings()
SETTINGS = _wrap(RAW)

BORDER_SIZE = SETTINGS.general.BORDER_SIZE
GAME_WIDTH = SETTINGS.general.GAME_WIDTH
GAME_HEIGHT = SETTINGS.general.GAME_HEIGHT
COLUMN_WIDTH = SETTINGS.general.COLUMN_WIDTH
PIXEL_SIZE = SETTINGS.general.PIXEL_SIZE
FPS = SETTINGS.general.FPS
PHYSICS_TPS = SETTINGS.general.PHYSICS_TPS

MENU_WIDTH = COLUMN_WIDTH * 3
WINDOW_WIDTH = GAME_WIDTH + MENU_WIDTH
WINDOW_HEIGHT = GAME_HEIGHT

painted_colors = [(name, tuple(color)) for name, color in SETTINGS.ui.painted_colors]
BRUSH_SUBTOOLS = list(SETTINGS.ui.brush_subtools)
OBJECT_SUBTOOLS = list(SETTINGS.ui.object_subtools)
TOOLS = list(SETTINGS.ui.tools)

TOOL_SUBTYPES = {
    "Рисование": BRUSH_SUBTOOLS,
    "Объекты": OBJECT_SUBTOOLS,
    "Выбор цвета": painted_colors,
}
