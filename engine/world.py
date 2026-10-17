import pygame

from . import textures
from .particle import Particle
from .settings import *
from .textures import temperature_to_color

_CLEAR = (0, 0, 0, 0)

CHUNK_SIZE = SETTINGS.world.chunk_size
WAKE_MARGIN = SETTINGS.world.wake_margin
AWAKE_TICKS = SETTINGS.world.awake_ticks
AMBIENT = SETTINGS.world.ambient_temperature
THERMAL_THRESHOLD = SETTINGS.world.thermal_threshold
THERMAL_TTL = SETTINGS.world.thermal_ttl
THERMAL_INTERVAL = SETTINGS.world.thermal_interval


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
        self.bodies = []
        self.chunks_x = -(-width // CHUNK_SIZE)
        self.chunks_y = -(-height // CHUNK_SIZE)
        self.chunk_awake = [AWAKE_TICKS] * (self.chunks_x * self.chunks_y)
        self.wake_targets = [[self._wake_targets(x, y) for x in range(width)] for y in range(height)]
        chunk_count = self.chunks_x * self.chunks_y
        self.thermal_ttl = [0] * chunk_count
        self.thermal_hot = [False] * chunk_count
        self.thermal_targets = [[self._thermal_targets(x, y) for x in range(width)] for y in range(height)]

        self.init_borders()

    def cell_rgba(self, x, y, temperature=False):
        p = self.grid[y][x]
        if p is None:
            return _CLEAR
        mat = p.material
        if temperature and p.temperature is not None and not self.is_border(x, y):
            r, g, b = temperature_to_color(p.temperature)
            return (r, g, b, 255)
        if p.baked is not None:
            return p.baked
        if mat is not None and mat.texture_map:
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
            return (r, g, b, a)
        col = p.color
        alpha = int(mat.opacity * 255) if mat is not None else 255
        return (col[0], col[1], col[2], alpha)

    def draw_cell(self, x, y):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        rgba = self.cell_rgba(x, y, self.temperature_mode)
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

    def _thermal_targets(self, x, y):
        cx, cy = x // CHUNK_SIZE, y // CHUNK_SIZE
        lx, ly = x - cx * CHUNK_SIZE, y - cy * CHUNK_SIZE
        xs = [cx]
        if lx < 1 and cx > 0:
            xs.append(cx - 1)
        if lx >= CHUNK_SIZE - 1 and cx < self.chunks_x - 1:
            xs.append(cx + 1)
        ys = [cy]
        if ly < 1 and cy > 0:
            ys.append(cy - 1)
        if ly >= CHUNK_SIZE - 1 and cy < self.chunks_y - 1:
            ys.append(cy + 1)
        return tuple(j * self.chunks_x + i for j in ys for i in xs)

    def mark_thermal(self, x, y, particle):
        if abs(particle.temperature - AMBIENT) > THERMAL_THRESHOLD:
            ttl = self.thermal_ttl
            for i in self.thermal_targets[y][x]:
                ttl[i] = THERMAL_TTL
            self.thermal_hot[self.thermal_targets[y][x][0]] = True
        else:
            hot = self.thermal_hot
            for i in self.wake_targets[y][x]:
                if hot[i]:
                    self.thermal_ttl[i] = THERMAL_TTL

    def wake(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            awake = self.chunk_awake
            for i in self.wake_targets[y][x]:
                awake[i] = AWAKE_TICKS

    def region_awake(self, x0, y0, x1, y1):
        cx0 = max(0, (x0 - 1) // CHUNK_SIZE)
        cx1 = min(self.chunks_x - 1, (x1 + 1) // CHUNK_SIZE)
        cy0 = max(0, (y0 - 1) // CHUNK_SIZE)
        cy1 = min(self.chunks_y - 1, (y1 + 1) // CHUNK_SIZE)
        awake = self.chunk_awake
        for cy in range(cy0, cy1 + 1):
            base = cy * self.chunks_x
            for cx in range(cx0, cx1 + 1):
                if awake[base + cx] > 0:
                    return True
        return False

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
        moved = self.grid[ny][nx]
        if moved is not None:
            self.mark_thermal(nx, ny, moved)
        if target is not None:
            self.mark_thermal(x, y, target)

    def set(self, x, y, particle):
        if self.in_bounds(x, y) and not self.is_border(x, y):
            self.grid[y][x] = particle
            self.draw_cell(x, y)
            awake = self.chunk_awake
            for i in self.wake_targets[y][x]:
                awake[i] = AWAKE_TICKS
            if particle is not None:
                self.mark_thermal(x, y, particle)

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
        for cx_, cy_ in ((x1, y1), (x2, y2)):
            q = self.grid[cy_][cx_]
            if q is not None:
                self.mark_thermal(cx_, cy_, q)

        return True

    def precompute_textures(self, progress=None):
        textures.precompute_textures(self.width, self.height, progress)

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
