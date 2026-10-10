from .constants import *
from .font import draw_text
from .particle import Particle
from .draw import temperature_to_color
import pygame

_CLEAR = (0, 0, 0, 0)

CHUNK_SIZE = 16
WAKE_MARGIN = 3
AWAKE_TICKS = 3


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
        self.temperature_mode = False
        self.tick_count = 0
        self.drawn_tick = -1

        self.sleep_enabled = True
        self.chunks_x = -(-width // CHUNK_SIZE)
        self.chunks_y = -(-height // CHUNK_SIZE)
        self.chunk_awake = [AWAKE_TICKS] * (self.chunks_x * self.chunks_y)
        self.wake_targets = [[self._wake_targets(x, y) for x in range(width)] for y in range(height)]

        self.init_borders()

    def draw_cell(self, x, y):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return

        p = self.grid[y][x]
        if p is None:
            rgba = _CLEAR
        else:
            mat = p.material
            if self.temperature_mode and p.temperature is not None and not self.is_border(x, y):
                r, g, b = temperature_to_color(p.temperature)
                rgba = (r, g, b, 255)
            elif mat is not None and mat.texture_map:
                try:
                    base = mat.texture_map[(x, y)]
                except KeyError:
                    base = (*mat.color, 255)
                r, g, b, a = base
                if mat.paintable and p.color != mat.color:
                    tr, tg, tb = p.color
                    r = r * tr // 255
                    g = g * tg // 255
                    b = b * tb // 255
                rgba = (r, g, b, a)
            else:
                col = p.color
                alpha = int(mat.opacity * 255) if mat is not None else 255
                rgba = (col[0], col[1], col[2], alpha)

        self.surface.fill(rgba, (x * PIXEL_SIZE, y * PIXEL_SIZE, PIXEL_SIZE, PIXEL_SIZE))

    def redraw_all(self):
        self.drawn_tick = self.tick_count
        for y in range(BORDER_SIZE, self.height - BORDER_SIZE):
            for x in range(BORDER_SIZE, self.width - BORDER_SIZE):
                self.draw_cell(x, y)

    def redraw_particles(self):
        grid = self.grid
        for y in range(BORDER_SIZE, self.height - BORDER_SIZE):
            row = grid[y]
            for x in range(BORDER_SIZE, self.width - BORDER_SIZE):
                if row[x] is not None:
                    self.draw_cell(x, y)

    def _wake_targets(self, x, y):
        cx, cy = x // CHUNK_SIZE, y // CHUNK_SIZE
        lx, ly = x - cx * CHUNK_SIZE, y - cy * CHUNK_SIZE
        xs = [cx]
        if lx < WAKE_MARGIN and cx > 0:
            xs.append(cx - 1)
        if lx >= CHUNK_SIZE - WAKE_MARGIN and cx < self.chunks_x - 1:
            xs.append(cx + 1)
        ys = [cy]
        if ly < WAKE_MARGIN and cy > 0:
            ys.append(cy - 1)
        if ly >= CHUNK_SIZE - WAKE_MARGIN and cy < self.chunks_y - 1:
            ys.append(cy + 1)
        return tuple(j * self.chunks_x + i for j in ys for i in xs)

    def wake(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            awake = self.chunk_awake
            for i in self.wake_targets[y][x]:
                awake[i] = AWAKE_TICKS

    def wake_all(self):
        self.chunk_awake = [AWAKE_TICKS] * len(self.chunk_awake)

    def move_to(self, x, y, nx, ny):
        grid = self.grid
        target = grid[ny][nx]
        grid[ny][nx] = grid[y][x]
        grid[y][x] = target
        self.draw_cell(x, y)
        self.draw_cell(nx, ny)
        awake = self.chunk_awake
        for i in self.wake_targets[y][x]:
            awake[i] = AWAKE_TICKS
        for i in self.wake_targets[ny][nx]:
            awake[i] = AWAKE_TICKS

    def set(self, x, y, particle):
        if self.in_bounds(x, y) and not self.is_border(x, y):
            self.grid[y][x] = particle
            self.draw_cell(x, y)
            awake = self.chunk_awake
            for i in self.wake_targets[y][x]:
                awake[i] = AWAKE_TICKS

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
        awake = self.chunk_awake
        for i in self.wake_targets[y1][x1]:
            awake[i] = AWAKE_TICKS
        for i in self.wake_targets[y2][x2]:
            awake[i] = AWAKE_TICKS

        return True

    def precompute_textures(self, screen):
        from .draw import evaluate_texture_color, frame_same_cache, tile_cache, LazyTextureMap
        from .materials import all_materials

        count = len(all_materials)
        for index, material in enumerate(all_materials):
            frame_same_cache.clear()
            tile_cache.clear()
            material.texture_map = {}

            if isinstance(material.texture, tuple) and material.texture[0] and material.texture[0][0]:
                texture, palette = material.texture
                height = len(texture)
                width = max(len(line) for line in texture)
                additional_colors = {}
                for key, expr in palette.items():
                    if expr.startswith("additional("):
                        inner = expr[11:-1].strip("() ")
                        try:
                            r, g, b = map(int, inner.split(","))
                            additional_colors[key] = (r, g, b)
                        except ValueError:
                            additional_colors[key] = material.color

                base_color = material.color
                opacity = int(material.opacity * 255)
                exprs = list(palette.values())
                order_dependent = any("same(" in e or "for_tile(" in e for e in exprs)
                deterministic = not any(("random" in e or "randint" in e) for e in exprs)
                char_memo = {}

                def make(x, y, texture=texture, palette=palette, base_color=base_color,
                         opacity=opacity, width=width, height=height,
                         additional_colors=additional_colors, deterministic=deterministic,
                         char_memo=char_memo):
                    char = texture[y % len(texture)][x % len(texture[0])]
                    if deterministic:
                        cached = char_memo.get(char)
                        if cached is not None:
                            return cached
                    tile_key = (x // width if width > 0 else 0, y // height if height > 0 else 0)
                    color_rgb = evaluate_texture_color(
                        char, palette, base_color, x, y, width, height,
                        additional_colors, tile_key
                    )
                    value = (*color_rgb, opacity)
                    if deterministic:
                        char_memo[char] = value
                    return value

                if order_dependent:
                    texture_map = {}
                    for y in range(self.height):
                        for x in range(self.width):
                            texture_map[(x, y)] = make(x, y)
                    material.texture_map = texture_map
                else:
                    material.texture_map = LazyTextureMap(lambda key, make=make: make(key[0], key[1]))

            if screen is not None:
                draw_loading_screen(screen, (index + 1) / count)

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
