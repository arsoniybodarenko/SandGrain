import pygame

from .settings import *
from .font import draw_text

_highlight = None


def draw_world(screen, world, temperature_mode=False):
    if world.temperature_mode != temperature_mode:
        world.temperature_mode = temperature_mode
        world.redraw_all()
    elif temperature_mode and world.drawn_tick != world.tick_count:
        world.drawn_tick = world.tick_count
        world.redraw_particles()
    screen.blit(world.surface, (0, 0))


def draw_overlay(screen, state):
    global _highlight
    world = state.world
    if _highlight is None:
        _highlight = pygame.Surface((PIXEL_SIZE, PIXEL_SIZE), pygame.SRCALPHA)
        _highlight.fill(tuple(SETTINGS.menu.selection_highlight))

    if state.selected_tool == "Объекты":
        for body in world.bodies:
            for (bx, by) in body.cover:
                screen.blit(_highlight, (bx * PIXEL_SIZE, by * PIXEL_SIZE))
        if state.selection_start is not None and state.selected_subtool == "Рамка":
            ex, ey = state.selection_end or state.selection_start
            rx0, rx1 = sorted((state.selection_start[0], ex))
            ry0, ry1 = sorted((state.selection_start[1], ey))
            pygame.draw.rect(screen, (255, 255, 255),
                             (rx0 * PIXEL_SIZE, ry0 * PIXEL_SIZE,
                              (rx1 - rx0 + 1) * PIXEL_SIZE, (ry1 - ry0 + 1) * PIXEL_SIZE), 2)

    if state.notice_text and pygame.time.get_ticks() < state.notice_until:
        draw_text(screen, state.notice_text, 10, 10)
