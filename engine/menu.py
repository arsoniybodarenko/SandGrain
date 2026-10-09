from .materials import MATERIALS, load_icon
from .multipixel import *
from .constants import *
from .draw import evaluate_texture

use_white_border = True


def branch_color(seed):
    rng = (seed * 928371 + 49217) % 100000
    shift = 255 - (rng % 100)
    return (shift, shift, shift)


def toggle_border_style():
    global use_white_border
    use_white_border = not use_white_border


def adjust_color(color, amount):
    return tuple(
        max(0, min(255, c + amount))
        for c in color
    )


def get_selected_material(selected_base, selected_variant):
    if selected_variant and selected_variant in MATERIALS:
        return selected_variant
    elif selected_base and selected_base in MATERIALS:
        return selected_base
    return None


def draw_icon(surface, icon_pixels, x, y, scale=4):
    for iy, row in enumerate(icon_pixels):
        for ix, color in enumerate(row):
            rect = pygame.Rect(x + ix * scale, y + iy * scale, scale, scale)
            pygame.draw.rect(surface, color, rect)


def get_category_icon(name):
    return load_icon(name)


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


icon_cache = {}


def get_cached_icon(label, item_type="material"):
    key = (label, item_type)
    if key in icon_cache:
        return icon_cache[key]

    surface = pygame.Surface((40, 40), pygame.SRCALPHA)

    if item_type == "material" and label in MATERIALS:
        mat = MATERIALS[label]
        icon = load_icon(label)
        if icon:
            draw_icon(surface, icon, 0, 0, scale=4)
        elif mat.texture and mat.texture[0]:
            pixels = evaluate_texture(mat.texture, base_color=mat.color)
            draw_icon(surface, pixels, 0, 0, scale=4)
        else:
            pygame.draw.rect(surface, mat.color, surface.get_rect())

    elif item_type == "tool":
        pygame.draw.rect(surface, (180, 180, 180), surface.get_rect())
        icon = load_icon(label)
        if icon:
            draw_icon(surface, icon, 0, 0, scale=4)

    elif item_type == "group":
        pygame.draw.rect(surface, (150, 150, 150), surface.get_rect())
        icon = get_category_icon(label)
        if icon:
            draw_icon(surface, icon, 0, 0, scale=4)

    elif item_type == "subtool":
        pygame.draw.rect(surface, (100, 100, 100), surface.get_rect())
        icon = load_icon(label)
        if icon:
            draw_icon(surface, icon, 0, 0, scale=4)

    elif item_type == "color":
        pygame.draw.rect(surface, label, surface.get_rect())

    else:
        pygame.draw.rect(surface, (100, 100, 100), surface.get_rect())

    icon_cache[key] = surface
    return surface


def draw_column(surface, x, items, selected, scroll_offset, item_type="material"):
    y_offset = 10 - scroll_offset
    for item in items:
        if isinstance(item, tuple):
            label, value = item
        else:
            label, value = str(item), item

        rect = pygame.Rect(x, y_offset, 40, 40)
        icon_surface = get_cached_icon(label if item_type != "color" else value, item_type)
        surface.blit(icon_surface, rect.topleft)

        if item_type == "color":
            if selected == value:
                border_color = (255, 255, 255) if use_white_border else adjust_color((150, 150, 150), -60)
                pygame.draw.rect(surface, border_color, rect, 4)
        else:
            if selected == item or selected == label:
                border_color = (255, 255, 255) if use_white_border else adjust_color((150, 150, 150), -60)
                pygame.draw.rect(surface, border_color, rect, 4)

        y_offset += 60


def draw_menus(menu_surface, selected_material,
               scroll_variant=0, scroll_base=0, scroll_group=0, scroll_tool=0,
               displaying_variant=None, displaying_base=None, displaying_group=None,
               selected_tool=None, selected_subtool=None, selected_color=None, scroll_subtool=0):
    pygame.draw.rect(menu_surface, (0, 0, 0), (0, 0, MENU_WIDTH, GAME_HEIGHT))

    if displaying_base and displaying_base in MATERIALS:
        if MATERIALS[displaying_base].category[0] != displaying_group:
            displaying_variant = None

    variant_items = []
    if displaying_base and displaying_base in MATERIALS:
        if MATERIALS[displaying_base].category[0] == displaying_group:
            variant_items = [
                name for name, mat in MATERIALS.items()
                if len(mat.category) == 3 and mat.category[1] == displaying_base
            ]

    if variant_items:
        draw_column(menu_surface, 10, variant_items, displaying_variant, scroll_variant, item_type="material")

    base_items = [
        name for name, mat in MATERIALS.items()
        if mat.category[0] == displaying_group and (
                len(mat.category) == 2 or (len(mat.category) == 3 and mat.category[2] == 0)
        )
    ]
    draw_column(menu_surface, 70, base_items, displaying_base, scroll_base, item_type="material")
    groups = sorted(set(mat.category[0] for mat in MATERIALS.values()))
    draw_column(menu_surface, 130, groups, displaying_group, scroll_group, item_type="group")

    tools = ["Рисование"]
    if selected_material in MATERIALS and MATERIALS[selected_material].paintable:
        tools.append("Выбор цвета")

    draw_column(menu_surface, 250, tools, selected_tool, scroll_tool, item_type="tool")

    if selected_tool in TOOL_SUBTYPES:
        sub_items = TOOL_SUBTYPES[selected_tool]
        item_type = "subtool" if selected_tool == "Рисование" else "color"
        selected = selected_subtool if item_type == "subtool" else selected_color
        draw_column(menu_surface, 190, sub_items, selected, scroll_subtool, item_type=item_type)

    draw_branches(
        menu_surface,
        groups, base_items, variant_items,
        scroll_group, scroll_base, scroll_variant,
        displaying_group, displaying_base,
        130, 70, 50,
        mode="material"
    )

    if selected_tool in TOOL_SUBTYPES and selected_tool != "Выбор цвета":
        sub_items = TOOL_SUBTYPES[selected_tool]
        selected = selected_subtool
        draw_branches(
            menu_surface,
            [selected_tool], sub_items, [],
            scroll_tool, scroll_subtool, 0,
            selected_tool, selected,
            250, 190, 210,
            mode="tool"
        )

    if selected_tool == "Выбор цвета":
        sub_items = TOOL_SUBTYPES["Выбор цвета"]
        draw_branches(
            menu_surface,
            ["Выбор цвета"], sub_items, [],
            scroll_tool, scroll_subtool, 0,
            "Выбор цвета", selected_color,
            250, 190, 210,
            mode="color"
        )

    preview_type = displaying_variant if displaying_variant else displaying_base
    return preview_type, displaying_variant


def draw_branches(surface,
                  parent_items, child_items, subchild_items,
                  scroll_parent, scroll_child, scroll_subchild,
                  displaying_parent, displaying_child,
                  parent_x, child_x, subchild_x,
                  mode="material"):
    def get_center(index, scroll):
        return 10 + index * 60 - scroll + 20

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
                if mode == "color":
                    parent_y = 100
                color = branch_color(hash((parent, child)) % 1000)
                draw_curve(
                    surface,
                    (child_x + 40, child_y),
                    (parent_x, parent_y),
                    offset=30,
                    color=color
                )

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
                    if isinstance(sub, tuple):
                        sub_label = sub[0]
                    else:
                        sub_label = sub
                    valid = sub_label in [s[0] if isinstance(s, tuple) else s for s in subchild_items]

                if valid:
                    sub_y = get_center(si, scroll_subchild)
                    color = branch_color(hash((child, sub)) % 1000)
                    draw_curve(
                        surface,
                        (subchild_x, sub_y),
                        (child_x, child_y),
                        offset=30,
                        color=color
                    )


def get_hovered_in_column(mx, my, column_x, items, scroll_offset):
    y_offset = 10 - scroll_offset
    for name in items:
        rect = pygame.Rect(column_x, y_offset, 40, 40)
        if rect.collidepoint(mx, my):
            return name
        y_offset += 60
    return None
