import pygame

from .. import filework
from ..font import draw_text, get_font
from ..materials import MATERIALS
from ..settings import *
from ..textures import adjust_color, branch_color, evaluate_texture, stable_seed
from . import menu_input
from .menu_input import ITEM_SIZE, ITEM_STEP, TOP_MARGIN, COLUMN_X

MENU = SETTINGS.menu
use_white_border = True
icon_cache = {}


def draw_loading_screen(screen, progress):
    screen.fill((0, 0, 0))
    draw_text(screen, MENU.loading_text, screen.get_width() // 2 - 140, screen.get_height() // 2 - 40)

    bar_width = MENU.loading_bar_width
    bar_height = MENU.loading_bar_height
    bar_x = (screen.get_width() - bar_width) // 2
    bar_y = screen.get_height() // 2

    pygame.draw.rect(screen, (80, 80, 80), (bar_x, bar_y, bar_width, bar_height))
    pygame.draw.rect(screen, (200, 200, 255), (bar_x, bar_y, int(bar_width * progress), bar_height))
    pygame.display.update()


def draw_icon(surface, icon_pixels, x, y, scale=4):
    for iy, row in enumerate(icon_pixels):
        for ix, color in enumerate(row):
            pygame.draw.rect(surface, color, pygame.Rect(x + ix * scale, y + iy * scale, scale, scale))


def draw_curve(surface, start, end, offset=40, color=(255, 255, 255), width=4):
    sx, sy = start
    ex, ey = end
    ctrl1 = (sx + offset, sy)
    ctrl2 = (ex - offset, ey)
    points = []
    for t in [i / 20.0 for i in range(21)]:
        x = (1 - t) ** 3 * sx + 3 * (1 - t) ** 2 * t * ctrl1[0] + 3 * (1 - t) * t ** 2 * ctrl2[0] + t ** 3 * ex
        y = (1 - t) ** 3 * sy + 3 * (1 - t) ** 2 * t * ctrl1[1] + 3 * (1 - t) * t ** 2 * ctrl2[1] + t ** 3 * ey
        points.append((int(x), int(y)))
    if sy == ey:
        pygame.draw.line(surface, color, start, end, width)
        return
    pygame.draw.lines(surface, color, False, points, width)


def get_cached_icon(label, item_type="material"):
    key = (label, item_type)
    if key in icon_cache:
        return icon_cache[key]

    surface = pygame.Surface((ITEM_SIZE, ITEM_SIZE), pygame.SRCALPHA)
    backgrounds = {"tool": (180, 180, 180), "group": (150, 150, 150), "subtool": (100, 100, 100)}

    if item_type == "material" and label in MATERIALS:
        mat = MATERIALS[label]
        icon = filework.load_icon(label)
        if icon:
            draw_icon(surface, icon, 0, 0)
        elif mat.texture and mat.texture[0]:
            draw_icon(surface, evaluate_texture(mat.texture, base_color=mat.color), 0, 0)
        else:
            pygame.draw.rect(surface, mat.color, surface.get_rect())
    elif item_type in backgrounds:
        pygame.draw.rect(surface, backgrounds[item_type], surface.get_rect())
        icon = filework.load_icon(label)
        if icon:
            draw_icon(surface, icon, 0, 0)
    elif item_type == "color":
        pygame.draw.rect(surface, label, surface.get_rect())
    else:
        pygame.draw.rect(surface, (100, 100, 100), surface.get_rect())

    icon_cache[key] = surface
    return surface


def draw_column(surface, x, items, selected, scroll_offset, item_type="material"):
    y_offset = TOP_MARGIN - scroll_offset
    border_color = (255, 255, 255) if use_white_border else adjust_color((150, 150, 150), -60)
    for item in items:
        label, value = item if isinstance(item, tuple) else (str(item), item)
        rect = pygame.Rect(x, y_offset, ITEM_SIZE, ITEM_SIZE)
        surface.blit(get_cached_icon(label if item_type != "color" else value, item_type), rect.topleft)

        if item_type == "color":
            if selected == value:
                pygame.draw.rect(surface, border_color, rect, 4)
        elif selected == item or selected == label:
            pygame.draw.rect(surface, border_color, rect, 4)

        y_offset += ITEM_STEP


def draw_branches(surface, parent_items, child_items, subchild_items,
                  scroll_parent, scroll_child, scroll_subchild,
                  displaying_parent, displaying_child,
                  parent_x, child_x, subchild_x, mode="material"):
    def get_center(index, scroll):
        return TOP_MARGIN + index * ITEM_STEP - scroll + ITEM_SIZE // 2

    for pi, parent in enumerate(parent_items):
        if parent != displaying_parent:
            continue
        parent_y = get_center(pi, scroll_parent)
        for ci, child in enumerate(child_items):
            valid = False
            if mode == "material":
                valid = child in MATERIALS and MATERIALS[child].category[0] == parent
            elif mode == "tool":
                valid = True

            if valid:
                child_y = get_center(ci, scroll_child)
                draw_curve(surface, (child_x + ITEM_SIZE, child_y), (parent_x, parent_y),
                           offset=30, color=branch_color(stable_seed(parent, child)))

    if displaying_child:
        for ci, child in enumerate(child_items):
            child_value = child[1] if isinstance(child, tuple) else child
            if mode == "color" and child_value != displaying_child:
                continue
            elif mode != "color" and child != displaying_child:
                continue

            child_y = get_center(ci, scroll_child)

            for si, sub in enumerate(subchild_items):
                valid = False
                if mode == "material":
                    valid = sub in MATERIALS and MATERIALS[sub].category[1] == child
                if mode == "color":
                    child_y = 100
                elif mode == "tool":
                    sub_label = sub[0] if isinstance(sub, tuple) else sub
                    valid = sub_label in [s[0] if isinstance(s, tuple) else s for s in subchild_items]

                if valid:
                    sub_y = get_center(si, scroll_subchild)
                    draw_curve(surface, (subchild_x, sub_y), (child_x, child_y),
                               offset=30, color=branch_color(stable_seed(child, sub)))


def draw_menus(state):
    surface = state.menu_surface
    scroll = state.scroll
    pygame.draw.rect(surface, tuple(MENU.background), (0, 0, MENU_WIDTH, GAME_HEIGHT))

    base = state.displaying_base
    if base and base in MATERIALS and MATERIALS[base].category[0] != state.displaying_group:
        state.displaying_variant = None

    variants = menu_input.variant_items(state)
    bases = menu_input.base_items(state)
    groups = menu_input.group_items()
    tools = menu_input.tool_items(state)
    x = COLUMN_X

    if variants:
        draw_column(surface, x["variant"], variants, state.displaying_variant, scroll["variant"])
    draw_column(surface, x["base"], bases, state.displaying_base, scroll["base"])
    draw_column(surface, x["group"], groups, state.displaying_group, scroll["group"], item_type="group")
    draw_column(surface, x["tool"], tools, state.selected_tool, scroll["tool"], item_type="tool")

    if state.selected_tool in TOOL_SUBTYPES:
        sub_items = TOOL_SUBTYPES[state.selected_tool]
        is_color = state.selected_tool == "Выбор цвета"
        draw_column(surface, x["subtool"], sub_items,
                    state.selected_color if is_color else state.selected_subtool,
                    scroll["subtool"], item_type="color" if is_color else "subtool")

    draw_branches(surface, groups, bases, variants,
                  scroll["group"], scroll["base"], scroll["variant"],
                  state.displaying_group, state.displaying_base,
                  x["group"], x["base"], x["variant"] + ITEM_SIZE, mode="material")

    if state.selected_tool in TOOL_SUBTYPES:
        sub_items = TOOL_SUBTYPES[state.selected_tool]
        if state.selected_tool == "Выбор цвета":
            draw_branches(surface, tools, sub_items, [],
                          scroll["tool"], scroll["subtool"], 0,
                          "Выбор цвета", state.selected_color,
                          x["tool"], x["subtool"], x["subtool"] + 20, mode="color")
        else:
            draw_branches(surface, tools, sub_items, [],
                          scroll["tool"], scroll["subtool"], 0,
                          state.selected_tool, state.selected_subtool,
                          x["tool"], x["subtool"], x["subtool"] + 20, mode="tool")

    state.preview_type = state.displaying_variant if state.displaying_variant else state.displaying_base


def draw_hover_text(screen, state):
    mx, my = pygame.mouse.get_pos()
    _, item = menu_input.hovered(state, mx, my)
    state.hovered_name = item
    if item:
        text = item[0] if isinstance(item, tuple) else str(item)
        text_width, text_height = get_font().size(text)
        draw_text(screen, text, mx - text_width, my - text_height + 20)
