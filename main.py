import pygame

from engine import input as game_input
from engine.draw import draw_overlay, draw_world
from engine.font import init_font
from engine.menu import menu
from engine.objects import update_bodies
from engine.physics.physics import tick_physics
from engine.settings import *
from engine.state import GameState
from engine.timing import FixedTimestep
from engine.world import World

pygame.init()
init_font()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Песчинка")
clock = pygame.time.Clock()

world = World(GAME_WIDTH // PIXEL_SIZE, GAME_HEIGHT // PIXEL_SIZE)
world.precompute_textures(lambda progress: menu.draw_loading_screen(screen, progress))

state = GameState(world)
physics_clock = FixedTimestep(PHYSICS_TPS)
frame_seconds = 0.0
sky_color = tuple(SETTINGS.world.sky_color)

while state.running:
    for event in pygame.event.get():
        game_input.handle_event(event, state)
    game_input.update(state)

    for _ in range(physics_clock.advance(frame_seconds)):
        tick_physics(world)
        update_bodies(world)

    screen.fill(sky_color)
    draw_world(screen, world, state.temperature_mode)
    draw_overlay(screen, state)

    if state.menu_dirty:
        menu.draw_menus(state)
        state.menu_dirty = False
    screen.blit(state.menu_surface, (GAME_WIDTH, 0))
    menu.draw_hover_text(screen, state)

    pygame.display.flip()
    frame_seconds = clock.tick(FPS) / 1000.0

pygame.quit()
