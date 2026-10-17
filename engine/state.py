import pygame

from .settings import *


class GameState:
    def __init__(self, world):
        defaults = SETTINGS.ui.defaults
        color_name, color_value = defaults.color

        self.world = world
        self.menu_surface = pygame.Surface((MENU_WIDTH, GAME_HEIGHT))
        self.running = True

        self.mouse_down = False
        self.brush_radius = defaults.brush_radius
        self.last_mouse_pos = None
        self.temperature_mode = False

        self.selected_tool = defaults.tool
        self.selected_material = defaults.material
        self.selected_subtool = defaults.subtool
        self.selected_color = tuple(color_value)
        self.previous_brush = defaults.subtool

        self.displaying_group = defaults.group
        self.displaying_base = defaults.base
        self.displaying_variant = defaults.variant
        self.displaying_color = (color_name, tuple(color_value))

        self.scroll = {name: 0 for name in vars(SETTINGS.menu.columns)}
        self.menu_dirty = True
        self.hovered_name = None
        self.preview_type = None

        self.selection_start = None
        self.selection_end = None
        self.notice_text = None
        self.notice_until = 0
