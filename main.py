import os
from datetime import datetime

import pygame

from engine.constants import *
from engine.draw import draw_world
from engine.font import init_font, draw_text, get_font
from engine.input import handle_event
from engine.menu import draw_menus
from engine.paint import *
from engine.physics.physics import tick_physics
from engine.world import World
from engine.menu import get_hovered_in_column

pygame.init()
init_font()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Песчинка")
clock = pygame.time.Clock()

menu_surface = pygame.Surface((MENU_WIDTH, GAME_HEIGHT))

GRID_WIDTH = GAME_WIDTH // PIXEL_SIZE
GRID_HEIGHT = GAME_HEIGHT // PIXEL_SIZE

world = World(GRID_WIDTH, GRID_HEIGHT)
world.precompute_textures(screen)

objects = []
brush_radius = 1
last_mouse_pos = None
mouse_down = False
erase_mode = False

selected_tool = "Рисование"
selected_material = "Песок"
selected_subtool = "Круглая кисть"
selected_color = (255, 255, 255)

displaying_group = "Строительство"
displaying_base = "Песок"
displaying_variant = "Песок"
displaying_color = ("Белый", (255, 255, 255))

scroll_group = 0
scroll_base = 0
scroll_variant = 0
scroll_tool = 0
scroll_subtool = 0

temperature_mode = False


def draw_hover_text(screen, mx, my,
                    displaying_base, displaying_group,
                    selected_tool, selected_material,
                    scroll_variant, scroll_base, scroll_group,
                    scroll_subtool, scroll_tool):
    hovered_name = None

    if GAME_WIDTH + 10 <= mx < GAME_WIDTH + 50:
        variant_items = [
            name for name, mat in MATERIALS.items()
            if displaying_base and len(mat.category) == 3 and mat.category[1] == displaying_base
        ]
        hovered_name = get_hovered_in_column(mx - GAME_WIDTH, my, 10, variant_items, scroll_variant)

    elif GAME_WIDTH + 70 <= mx < GAME_WIDTH + 110:
        base_items = [
            name for name, mat in MATERIALS.items()
            if mat.category[0] == displaying_group and (
                    len(mat.category) == 2 or (len(mat.category) == 3 and mat.category[2] == 0)
            )
        ]
        hovered_name = get_hovered_in_column(mx - GAME_WIDTH, my, 70, base_items, scroll_base)

    elif GAME_WIDTH + 130 <= mx < GAME_WIDTH + 170:
        groups = sorted(set(mat.category[0] for mat in MATERIALS.values()))
        hovered_name = get_hovered_in_column(mx - GAME_WIDTH, my, 130, groups, scroll_group)

    elif GAME_WIDTH + 190 <= mx < GAME_WIDTH + 230:
        if selected_tool in TOOL_SUBTYPES:
            sub_items = TOOL_SUBTYPES[selected_tool]
            hovered_name = get_hovered_in_column(mx - GAME_WIDTH, my, 190, sub_items, scroll_subtool)

    elif GAME_WIDTH + 250 <= mx < GAME_WIDTH + 290:
        tools = ["Рисование"]
        if selected_material in MATERIALS and MATERIALS[selected_material].paintable:
            tools.append("Выбор цвета")
        hovered_name = get_hovered_in_column(mx - GAME_WIDTH, my, 250, tools, scroll_tool)

    if hovered_name:
        hovered_text = hovered_name[0] if isinstance(hovered_name, tuple) else str(hovered_name)

        text_width, text_height = get_font().size(hovered_text)
        draw_text(screen, hovered_text, mx - text_width, my - text_height + 20)

    return hovered_name


def take_world_screenshot(world, objects):
    surface = pygame.Surface((world.width * PIXEL_SIZE, world.height * PIXEL_SIZE), flags=pygame.SRCALPHA, depth=32)

    surface.fill((100, 220, 250))
    for obj in objects:
        obj.draw(surface, pixel_size=PIXEL_SIZE, world=world)
    draw_world(surface, world)
    os.makedirs("screenshots", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"screenshots/world_{timestamp}.png"
    pygame.image.save(surface, filename)


# for x in range(GAME_WIDTH):
#    for y in range(GAME_HEIGHT):
#        if random.random() > 0.90:
#            world.set(x+2, y+2, Particle(None, color=None))

menu_dirty = True

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_t:
                temperature_mode = not temperature_mode
                for x in range(world.height * 2):
                    for y in range(world.width * 2):
                        if world.is_border(x, y):
                            continue
                        world.draw_cell(x, y)

        (
            mouse_down, brush_radius, erase_mode,
            selected_tool, selected_material,
            displaying_group, displaying_base, displaying_variant,
            scroll_group, scroll_base, scroll_variant, scroll_tool,
            selected_subtool, scroll_subtool,
            selected_color, displaying_color, menu_dirty_flag
        ) = handle_event(
            event,
            (
                mouse_down, brush_radius, erase_mode,
                selected_tool, selected_material,
                displaying_group, displaying_base, displaying_variant,
                scroll_group, scroll_base, scroll_variant, scroll_tool,
                selected_subtool, scroll_subtool,
                selected_color, displaying_color
            ),
            objects,
            world,
            take_world_screenshot
        )
        if menu_dirty_flag:
            menu_dirty = True

    mx, my = pygame.mouse.get_pos()
    gx, gy = mx // PIXEL_SIZE, my // PIXEL_SIZE

    if mouse_down and mx < GAME_WIDTH:
        if last_mouse_pos:
            lx, ly = last_mouse_pos
            draw_line(world, lx, ly, gx, gy, selected_material, brush_radius, erase=erase_mode,
                      brush_type=selected_subtool, selected_color=selected_color)

        else:
            apply_brush(world, gx, gy, selected_material, brush_radius, erase=erase_mode, brush_type=selected_subtool,
                        selected_color=selected_color)

        last_mouse_pos = (gx, gy)
    else:
        last_mouse_pos = None

    tick_physics(world)
    world.objects = objects
    for obj in objects:
        obj.update_physics(world)

    screen.fill((100, 220, 250))
    for obj in objects:
        obj.draw(screen, PIXEL_SIZE, world)
    draw_world(screen, world, temperature_mode)

    hovered_name = None

    if menu_dirty:
        preview_type, displaying_variant = draw_menus(
            menu_surface,
            selected_material,
            scroll_variant,
            scroll_base,
            scroll_group,
            scroll_tool,
            displaying_variant,
            displaying_base,
            displaying_group,
            selected_tool,
            selected_subtool,
            selected_color,
            scroll_subtool
        )
        menu_dirty = False

    screen.blit(menu_surface, (GAME_WIDTH, 0))

    hovered_name = draw_hover_text(
        screen, mx, my,
        displaying_base, displaying_group,
        selected_tool, selected_material,
        scroll_variant, scroll_base, scroll_group,
        scroll_subtool, scroll_tool
    )

    fps = clock.get_fps()

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
