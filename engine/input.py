import pygame

from . import filework
from .menu import menu_input
from .objects import grab_at, make_bodies, select_flood, select_rect, spawn_blob
from .paint import apply_brush, draw_line
from .physics import physics as _physics
from .settings import *

KEYS = SETTINGS.keys
GRAVITY_ROTATION = {"gravity_up": 180, "gravity_down": 0, "gravity_left": -90, "gravity_right": 90}
_keymap = None


def _code(name):
    try:
        return pygame.key.key_code(name)
    except ValueError:
        return None


def _bind(keymap, name, action):
    code = _code(name)
    if code is not None:
        keymap[code] = action


def build_keymap():
    keymap = {}
    for action in ("screenshot", "temperature_mode", "spawn_object", "select_material"):
        _bind(keymap, getattr(KEYS, action), (action,))
    for action, rotation in GRAVITY_ROTATION.items():
        _bind(keymap, getattr(KEYS, action), ("gravity", rotation))
    for index, name in enumerate(KEYS.brush_radius):
        _bind(keymap, name, ("radius", index + 1))
    for tool, name in vars(KEYS.tools).items():
        _bind(keymap, name, ("tool", tool))
    for tool, subtools in vars(KEYS.subtools).items():
        for subtool, name in vars(subtools).items():
            _bind(keymap, name, ("subtool", tool, subtool))
    return keymap


def keymap():
    global _keymap
    if _keymap is None:
        _keymap = build_keymap()
    return _keymap


def take_screenshot(state):
    world = state.world
    surface = pygame.Surface((world.width * PIXEL_SIZE, world.height * PIXEL_SIZE), flags=pygame.SRCALPHA, depth=32)
    surface.fill(tuple(SETTINGS.world.sky_color))
    surface.blit(world.surface, (0, 0))
    filework.save_screenshot(surface)


def choose_subtool(state, tool, subtool):
    if tool == "Рисование":
        if subtool == "Ластик":
            if state.selected_tool == tool and state.selected_subtool == "Ластик":
                subtool = state.previous_brush
            elif state.selected_subtool != "Ластик":
                state.previous_brush = state.selected_subtool
        else:
            state.previous_brush = subtool
    menu_input.select_subtool(state, tool, subtool)


def handle_key(event, state):
    action = keymap().get(event.key)
    if action is None:
        return
    name = action[0]

    if name == "screenshot":
        take_screenshot(state)
    elif name == "temperature_mode":
        state.temperature_mode = not state.temperature_mode
    elif name == "spawn_object":
        mx, my = pygame.mouse.get_pos()
        if mx < GAME_WIDTH:
            spawn_blob(state.world, mx // PIXEL_SIZE, my // PIXEL_SIZE)
    elif name == "select_material":
        state.selected_material = state.displaying_variant or state.displaying_base
        state.menu_dirty = True
    elif name == "gravity":
        _physics.physics_rotation = action[1]
    elif name == "radius":
        state.brush_radius = action[1]
    elif name == "tool":
        menu_input.select_tool(state, action[1])
    elif name == "subtool":
        choose_subtool(state, action[1], action[2])


def handle_event(event, state):
    if event.type == pygame.QUIT:
        state.running = False

    elif event.type == pygame.KEYDOWN:
        handle_key(event, state)

    elif event.type == pygame.MOUSEWHEEL:
        mx, _ = pygame.mouse.get_pos()
        menu_input.handle_wheel(state, mx, event.y)

    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        state.mouse_down = True
        mx, my = pygame.mouse.get_pos()
        menu_input.handle_click(state, mx, my)

    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
        state.mouse_down = False

    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
        mx, my = pygame.mouse.get_pos()
        if mx < GAME_WIDTH:
            grab_at(state.world, mx / PIXEL_SIZE, my / PIXEL_SIZE)


def update_grab(state, mx, my):
    right_pressed = pygame.mouse.get_pressed()[2]
    for body in state.world.bodies:
        if body.grab is not None:
            if right_pressed:
                body.grab = (mx / PIXEL_SIZE, my / PIXEL_SIZE)
            else:
                body.end_grab()


def update_selection(state, mx, my):
    world = state.world
    gx, gy = mx // PIXEL_SIZE, my // PIXEL_SIZE
    state.last_mouse_pos = None
    if state.mouse_down and mx < GAME_WIDTH:
        if state.selection_start is None:
            state.selection_start = (gx, gy)
        state.selection_end = (gx, gy)
    elif state.selection_start is not None:
        x0, y0 = state.selection_start
        x1, y1 = state.selection_end or state.selection_start
        if state.selected_subtool == "Заливка":
            coords = select_flood(world, x0, y0)
        else:
            coords = select_rect(world, x0, y0, x1, y1)
        _, skipped = make_bodies(world, coords)
        if skipped:
            state.notice_text = "Слишком большой объект"
            state.notice_until = pygame.time.get_ticks() + SETTINGS.menu.notice_duration_ms
        state.selection_start = state.selection_end = None


def update_painting(state, mx, my):
    state.selection_start = state.selection_end = None
    gx, gy = mx // PIXEL_SIZE, my // PIXEL_SIZE
    if state.mouse_down and mx < GAME_WIDTH:
        if state.last_mouse_pos:
            lx, ly = state.last_mouse_pos
            draw_line(state.world, lx, ly, gx, gy, state.selected_material, state.brush_radius, erase=False,
                      brush_type=state.selected_subtool, selected_color=state.selected_color)
        else:
            apply_brush(state.world, gx, gy, state.selected_material, state.brush_radius, erase=False,
                        brush_type=state.selected_subtool, selected_color=state.selected_color)
        state.last_mouse_pos = (gx, gy)
    else:
        state.last_mouse_pos = None


def update(state):
    mx, my = pygame.mouse.get_pos()
    update_grab(state, mx, my)
    if state.selected_tool == "Объекты":
        update_selection(state, mx, my)
    else:
        update_painting(state, mx, my)
