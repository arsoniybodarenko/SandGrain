import pygame

from .constants import *
from . import physics
from .materials import MATERIALS
from .multipixel import MultiPixelObject
from .menu import get_hovered_in_column


def handle_event(event, state, objects, world, take_screenshot):
    (
        mouse_down, brush_radius, erase,
        selected_tool, selected_material,
        displaying_group, displaying_base, displaying_variant,
        scroll_group, scroll_base, scroll_variant, scroll_tool,
        selected_subtool, scroll_subtool, selected_color, displaying_color
    ) = state

    menu_dirty = False

    if event.type == pygame.KEYDOWN:
        if pygame.K_1 <= event.key <= pygame.K_9:
            brush_radius = event.key - pygame.K_0

        elif event.key == pygame.K_F2:
            take_screenshot(world, objects)

        elif event.key == pygame.K_q:
            mx, my = pygame.mouse.get_pos()
            grid_x = mx // PIXEL_SIZE
            grid_y = my // PIXEL_SIZE
            objects.append(MultiPixelObject(grid_x, grid_y))

        elif event.key == pygame.K_e:
            erase = not erase
            if erase:
                selected_subtool = "Ластик"
            else:
                selected_subtool = "Круглая кисть"
            menu_dirty = True

        elif event.key == pygame.K_RETURN:
            selected_material = displaying_variant or displaying_base

        elif event.key == pygame.K_UP:
            physics.physics.physics_rotation = 180
        elif event.key == pygame.K_DOWN:
            physics.physics.physics_rotation = 0
        elif event.key == pygame.K_LEFT:
            physics.physics.physics_rotation = -90
        elif event.key == pygame.K_RIGHT:
            physics.physics.physics_rotation = 90

    if event.type == pygame.MOUSEWHEEL:
        menu_dirty = True
        mx, my = pygame.mouse.get_pos()
        item_height = 60
        visible_height = GAME_HEIGHT
        scroll_step = item_height
        scroll_subtool_target = scroll_subtool
        scroll_tool_target = scroll_tool
        scroll_base_target = scroll_base
        scroll_variant_target = scroll_variant
        scroll_group_target = scroll_group

        if GAME_WIDTH + 10 <= mx < GAME_WIDTH + 50:
            variant_items = [
                name for name, mat in MATERIALS.items()
                if displaying_base and len(mat.category) == 3 and mat.category[1] == displaying_base
            ]
            max_scroll = max(0, len(variant_items) * item_height - visible_height)
            scroll_variant_target = min(max(0, scroll_variant_target - event.y * scroll_step), max_scroll)

        elif GAME_WIDTH + 70 <= mx < GAME_WIDTH + 110:
            base_items = [
                name for name, mat in MATERIALS.items()
                if mat.category[0] == displaying_group and (
                        len(mat.category) == 2 or (len(mat.category) == 3 and mat.category[2] == 0)
                )
            ]
            max_scroll = max(0, len(base_items) * item_height - visible_height)
            scroll_base_target = min(max(0, scroll_base_target - event.y * scroll_step), max_scroll)

        elif GAME_WIDTH + 130 <= mx < GAME_WIDTH + 170:
            groups = sorted(set(mat.category[0] for mat in MATERIALS.values()))
            max_scroll = max(0, len(groups) * item_height - visible_height)
            scroll_group_target = min(max(0, scroll_group_target - event.y * scroll_step), max_scroll)

        elif GAME_WIDTH + 190 <= mx < GAME_WIDTH + 230:
            if selected_tool in TOOL_SUBTYPES:
                sub_items = TOOL_SUBTYPES[selected_tool]
                max_scroll = max(0, len(sub_items) * item_height - visible_height)
                scroll_subtool_target = min(max(0, scroll_subtool_target - event.y * scroll_step), max_scroll)

        elif GAME_WIDTH + 250 <= mx < GAME_WIDTH + 290:
            max_scroll = max(0, len(TOOLS) * item_height - visible_height)
            scroll_tool_target = min(max(0, scroll_tool_target - event.y * scroll_step), max_scroll)

        damping = 0.5

        scroll_base += (scroll_base_target - scroll_base) * damping
        scroll_variant += (scroll_variant_target - scroll_variant) * damping
        scroll_group += (scroll_group_target - scroll_group) * damping
        scroll_tool += (scroll_tool_target - scroll_tool) * damping
        scroll_subtool += (scroll_subtool_target - scroll_subtool) * damping

    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        menu_dirty = True
        mouse_down = True
        mx, my = pygame.mouse.get_pos()

        if GAME_WIDTH + 10 <= mx < GAME_WIDTH + 50:
            variant_items = [
                name for name, mat in MATERIALS.items()
                if len(mat.category) == 3 and mat.category[1] == displaying_base
            ]
            hovered = get_hovered_in_column(mx, my, GAME_WIDTH + 10, variant_items, scroll_variant)
            if hovered:
                displaying_variant = hovered
                selected_material = hovered

        elif GAME_WIDTH + 70 <= mx < GAME_WIDTH + 110:
            base_items = [
                name for name, mat in MATERIALS.items()
                if mat.category[0] == displaying_group and (
                        len(mat.category) == 2 or (len(mat.category) == 3 and mat.category[2] == 0)
                )
            ]
            hovered = get_hovered_in_column(mx, my, GAME_WIDTH + 70, base_items, scroll_base)
            if hovered:
                displaying_base = hovered
                displaying_variant = None
                if hovered in MATERIALS:
                    selected_material = hovered


        elif GAME_WIDTH + 130 <= mx < GAME_WIDTH + 170:
            groups = sorted(set(mat.category[0] for mat in MATERIALS.values()))
            hovered = get_hovered_in_column(mx, my, GAME_WIDTH + 130, groups, scroll_group)
            if hovered:
                displaying_group = hovered
                scroll_base = 0
                scroll_variant = 0
                if displaying_base and MATERIALS[displaying_base].category[0] != displaying_group:
                    displaying_variant = None

        elif GAME_WIDTH + 190 <= mx < GAME_WIDTH + 230:
            if selected_tool == "Выбор цвета":
                sub_items = TOOL_SUBTYPES["Выбор цвета"]
                hovered = get_hovered_in_column(mx, my, GAME_WIDTH + 190, sub_items, scroll_subtool)
                if hovered:
                    displaying_color = hovered[1] if isinstance(hovered, tuple) else hovered
                    selected_color = displaying_color
                    # selected_tool = "Рисование"
                    # selected_subtool = selected_subtool or "Круглая кисть"

            elif selected_tool in TOOL_SUBTYPES:
                sub_items = TOOL_SUBTYPES[selected_tool]
                hovered = get_hovered_in_column(mx, my, GAME_WIDTH + 190, sub_items, scroll_subtool)
                if hovered:
                    selected_subtool = hovered

        elif GAME_WIDTH + 250 <= mx < GAME_WIDTH + 290:
            tools = ["Рисование"]
            if selected_material in MATERIALS and MATERIALS[selected_material].paintable:
                tools.append("Выбор цвета")

            if selected_tool not in tools:
                selected_tool = "Рисование"
                selected_subtool = selected_subtool or "Круглая кисть"
                displaying_color = None

            hovered = get_hovered_in_column(mx, my, GAME_WIDTH + 250, tools, scroll_tool)
            if hovered:
                selected_tool = hovered
                scroll_tool = 0
                scroll_subtool = 0

    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
        mouse_down = False

    for obj in objects:
        obj.handle_event(event, PIXEL_SIZE, world)

    return (
        mouse_down, brush_radius, erase,
        selected_tool, selected_material,
        displaying_group, displaying_base, displaying_variant,
        scroll_group, scroll_base, scroll_variant, scroll_tool,
        selected_subtool, scroll_subtool,
        selected_color, displaying_color,
        menu_dirty
    )
