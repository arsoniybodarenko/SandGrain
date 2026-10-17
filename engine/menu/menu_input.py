import pygame

from ..materials import MATERIALS
from ..settings import *

MENU = SETTINGS.menu
ITEM_SIZE = MENU.item_size
ITEM_STEP = MENU.item_step
TOP_MARGIN = MENU.top_margin
COLUMN_X = vars(MENU.columns)


def available_tools(selected_material):
    tools = [tool for tool in TOOLS if tool != "Выбор цвета"]
    if selected_material in MATERIALS and MATERIALS[selected_material].paintable:
        tools.append("Выбор цвета")
    return tools


def variant_items(state):
    base = state.displaying_base
    if base and base in MATERIALS and MATERIALS[base].category[0] == state.displaying_group:
        return [name for name, mat in MATERIALS.items() if len(mat.category) == 3 and mat.category[1] == base]
    return []


def base_items(state):
    return [
        name for name, mat in MATERIALS.items()
        if mat.category[0] == state.displaying_group and (
                len(mat.category) == 2 or (len(mat.category) == 3 and mat.category[2] == 0)
        )
    ]


def group_items(state=None):
    return sorted(set(mat.category[0] for mat in MATERIALS.values()))


def tool_items(state):
    return available_tools(state.selected_material)


def subtool_items(state):
    return TOOL_SUBTYPES.get(state.selected_tool, [])


COLUMN_ITEMS = {
    "variant": variant_items,
    "base": base_items,
    "group": group_items,
    "tool": tool_items,
    "subtool": subtool_items,
}


def item_at(column_x, mx, my, items, scroll):
    y_offset = TOP_MARGIN - scroll
    for item in items:
        if pygame.Rect(column_x, y_offset, ITEM_SIZE, ITEM_SIZE).collidepoint(mx, my):
            return item
        y_offset += ITEM_STEP
    return None


def hovered(state, mx, my):
    if mx < GAME_WIDTH:
        return None, None
    rx = mx - GAME_WIDTH
    for column, x in COLUMN_X.items():
        if x <= rx < x + ITEM_SIZE:
            return column, item_at(x, rx, my, COLUMN_ITEMS[column](state), state.scroll[column])
    return None, None


def default_subtool(tool):
    if tool == "Объекты":
        return OBJECT_SUBTOOLS[0]
    return BRUSH_SUBTOOLS[0]


def select_tool(state, tool):
    tools = tool_items(state)
    if tool not in tools:
        return False
    state.selected_tool = tool
    state.scroll["tool"] = 0
    state.scroll["subtool"] = 0
    if tool == "Объекты":
        if state.selected_subtool not in OBJECT_SUBTOOLS:
            state.selected_subtool = OBJECT_SUBTOOLS[0]
    elif tool == "Рисование" and state.selected_subtool not in BRUSH_SUBTOOLS:
        state.selected_subtool = BRUSH_SUBTOOLS[0]
    state.menu_dirty = True
    return True


def select_subtool(state, tool, subtool):
    if not select_tool(state, tool):
        return False
    state.selected_subtool = subtool
    state.menu_dirty = True
    return True


def _click_variant(state, item):
    if item:
        state.displaying_variant = item
        state.selected_material = item


def _click_base(state, item):
    if item:
        state.displaying_base = item
        state.displaying_variant = None
        if item in MATERIALS:
            state.selected_material = item


def _click_group(state, item):
    if item:
        state.displaying_group = item
        state.scroll["base"] = 0
        state.scroll["variant"] = 0
        base = state.displaying_base
        if base and MATERIALS[base].category[0] != state.displaying_group:
            state.displaying_variant = None


def _click_subtool(state, item):
    if not item:
        return
    if state.selected_tool == "Выбор цвета":
        state.displaying_color = item if isinstance(item, tuple) else (str(item), item)
        state.selected_color = state.displaying_color[1]
    elif state.selected_tool in TOOL_SUBTYPES:
        state.selected_subtool = item


def _click_tool(state, item):
    if state.selected_tool not in tool_items(state):
        state.selected_tool = "Рисование"
        state.displaying_color = None
    if item:
        select_tool(state, item)
    elif state.selected_tool == "Объекты":
        if state.selected_subtool not in OBJECT_SUBTOOLS:
            state.selected_subtool = OBJECT_SUBTOOLS[0]
    elif state.selected_subtool not in BRUSH_SUBTOOLS:
        state.selected_subtool = BRUSH_SUBTOOLS[0]


COLUMN_CLICK = {
    "variant": _click_variant,
    "base": _click_base,
    "group": _click_group,
    "tool": _click_tool,
    "subtool": _click_subtool,
}


def handle_click(state, mx, my):
    column, item = hovered(state, mx, my)
    if column is not None:
        COLUMN_CLICK[column](state, item)
    state.menu_dirty = True
    return mx >= GAME_WIDTH


def handle_wheel(state, mx, wheel_y):
    state.menu_dirty = True
    if mx < GAME_WIDTH:
        return
    rx = mx - GAME_WIDTH
    for column, x in COLUMN_X.items():
        if x <= rx < x + ITEM_SIZE:
            items = COLUMN_ITEMS[column](state)
            max_scroll = max(0, len(items) * ITEM_STEP - GAME_HEIGHT)
            target = state.scroll[column] - wheel_y * MENU.scroll_step
            state.scroll[column] = min(max(0, target), max_scroll)
            return
