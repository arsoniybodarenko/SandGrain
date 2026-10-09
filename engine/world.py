from .constants import *
from .font import draw_text
from .particle import Particle
import pygame


def draw_loading_screen(screen, progress):

    screen.fill((0, 0, 0))

    draw_text(
        screen,
        "Генерация текстур...",
        screen.get_width() // 2 - 140,
        screen.get_height() // 2 - 40
    )

    bar_width = 400
    bar_height = 20
    bar_x = (screen.get_width() - bar_width) // 2
    bar_y = screen.get_height() // 2

    pygame.draw.rect(screen, (80, 80, 80), (bar_x, bar_y, bar_width, bar_height))
    pygame.draw.rect(screen, (200, 200, 255), (bar_x, bar_y, int(bar_width * progress), bar_height))

    pygame.display.update()


class World:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.grid = [[None for _ in range(width)] for _ in range(height)]
        self.surface = pygame.Surface((self.width * PIXEL_SIZE, self.height * PIXEL_SIZE), pygame.SRCALPHA)

        self.init_borders()

    def draw_cell(self, x, y):
        p = self.get(x, y)
        if not p:
            color = (0, 0, 0)
            alpha = 0
        elif p.material and p.material.texture_map:
            base_rgba = p.material.texture_map.get((x, y), (*p.material.color, 255))
            base_rgb = base_rgba[:3]
            alpha = base_rgba[3]

            if p.material.paintable and p.color != p.material.color:
                from .draw import apply_tint
                tinted_rgb = apply_tint([[base_rgb]], p.color)[0][0]
                color = tinted_rgb
            else:
                color = base_rgb
        else:
            color = p.color
            alpha = int(p.material.opacity * 255) if p.material else 255

        px = x * PIXEL_SIZE
        py = y * PIXEL_SIZE

        arr = pygame.surfarray.pixels3d(self.surface)
        arr[px:px + PIXEL_SIZE, py:py + PIXEL_SIZE] = color
        del arr

        arr_alpha = pygame.surfarray.pixels_alpha(self.surface)
        arr_alpha[px:px + PIXEL_SIZE, py:py + PIXEL_SIZE] = alpha
        del arr_alpha

    def set(self, x, y, particle):
        if self.in_bounds(x, y) and not self.is_border(x, y):
            self.grid[y][x] = particle
            self.draw_cell(x, y)

    def swap(self, x1, y1, x2, y2):
        if not (self.in_bounds(x1, y1) and self.in_bounds(x2, y2)):
            return False
        if self.is_border(x1, y1) or self.is_border(x2, y2):
            return False

        p1 = self.grid[y1][x1]
        p2 = self.grid[y2][x2]
        self.grid[y1][x1], self.grid[y2][x2] = p2, p1

        self.draw_cell(x1, y1)
        self.draw_cell(x2, y2)

        return True

    def precompute_textures(self, screen):
        from .draw import evaluate_texture_color
        from .materials import all_materials

        total = len(all_materials) * self.width * self.height
        done = 0

        for material in all_materials:
            from .draw import frame_same_cache, tile_cache
            frame_same_cache.clear()
            tile_cache.clear()

            if not isinstance(material.texture, tuple):
                material.texture_map.clear()
                continue

            texture, palette = material.texture
            if not texture or not texture[0]:
                material.texture_map.clear()
                continue

            height = len(texture)
            width = max(len(line) for line in texture) if texture else 0
            additional_colors = {}
            for key, expr in palette.items():
                if expr.startswith("additional("):
                    inner = expr[11:-1].strip("() ")
                    try:
                        r, g, b = map(int, inner.split(","))
                        additional_colors[key] = (r, g, b)
                    except ValueError:
                        additional_colors[key] = material.color

            material.texture_map.clear()

            for y in range(self.height):
                for x in range(self.width):
                    tile_x = x // width if width > 0 else 0
                    tile_y = y // height if height > 0 else 0
                    tile_key = (tile_x, tile_y)

                    base_color = material.color
                    opacity = int(material.opacity * 255)

                    tx = x % len(texture[0])
                    ty = y % len(texture)
                    char = texture[ty][tx]
                    color_rgb = evaluate_texture_color(
                        char, palette, base_color, x, y, width, height,
                        additional_colors, tile_key
                    )

                    material.texture_map[(x, y)] = (*color_rgb, opacity)

                    done += 1
                    if done % 500 == 0:
                        draw_loading_screen(screen, done / total)

    def init_borders(self):
        for y in range(self.height):
            for x in range(self.width):
                if (
                        x < BORDER_SIZE or x >= self.width - BORDER_SIZE or
                        y < BORDER_SIZE or y >= self.height - BORDER_SIZE
                ):
                    self.grid[y][x] = Particle("Творческая граница")
                    self.draw_cell(x, y)

    def in_bounds(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def is_border(self, x, y):
        return (
                x < BORDER_SIZE or x >= self.width - BORDER_SIZE or
                y < BORDER_SIZE or y >= self.height - BORDER_SIZE
        )

    def is_empty_or_liquid(self, x, y):
        if not self.in_bounds(x, y):
            return False
        target = self.get(x, y)
        if target is None:
            return True
        if target.material is None:
            return True
        return target.material.physics_type[0] == 2

    def move(self, x, y, nx, ny, particle):
        if not self.in_bounds(nx, ny):
            return False
        target = self.get(nx, ny)
        if target:
            self.swap(x, y, nx, ny)
        else:
            self.set(nx, ny, particle)
            self.set(x, y, None)
        return True

    def get(self, x, y):
        if self.in_bounds(x, y):
            return self.grid[y][x]
        return None
