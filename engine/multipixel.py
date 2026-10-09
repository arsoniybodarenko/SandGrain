import pygame
import math
import random
from .particle import Particle


class MultiPixelObject:
    def __init__(self, grid_x, grid_y, color=(100, 100, 100), world=None):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.color = color
        self.angle = 0.0
        self.dragging = False
        self.drag_offset = (0, 0)
        self.angular_velocity = 0.0
        self.was_falling = False
        self.fall_distance = 0

        shape_template = [
            [0, 1, 1, 0],
            [1, 1, 1, 1],
            [1, 1, 1, 1],
            [1, 1, 1, 1],
            [0, 1, 1, 0]
        ]
        self.local_pixels = [(dx, dy) for dy, row in enumerate(shape_template) for dx, val in enumerate(row) if val]
        self.width = len(shape_template[0])
        self.height = len(shape_template)

        if world and not self.is_fully_within_bounds(world):
            raise ValueError("Object out of bounds")

    def get_rotated_mask(self, world):
        angle_rad = math.radians(self.angle)
        cx, cy = self.width / 2 - 0.5, self.height / 2 - 0.5
        mask = set()

        for dx, dy in self.local_pixels:
            lx, ly = dx - cx, dy - cy
            rx = lx * math.cos(angle_rad) - ly * math.sin(angle_rad)
            ry = lx * math.sin(angle_rad) + ly * math.cos(angle_rad)
            gx, gy = self.grid_x + rx + cx, self.grid_y + ry + cy

            for ix in range(-1, 1):
                for iy in range(-1, 1):
                    x, y = int(round(gx)) + ix, int(round(gy)) + iy
                    if 0 <= x < world.width and 0 <= y < world.height:
                        mask.add((x, y))
        return mask

    def process_mask(self, raw_mask, world):
        return {(x, y) for (x, y) in raw_mask if 0 <= x < world.width and 0 <= y < world.height}

    def draw(self, surface, pixel_size, world):
        for x, y in self.process_mask(self.get_rotated_mask(world), world):
            pygame.draw.rect(surface, self.color, (x * pixel_size, y * pixel_size, pixel_size, pixel_size))

    def is_fully_within_bounds(self, world):
        return all(0 <= x < world.width and 0 <= y < world.height for x, y in
                   self.process_mask(self.get_rotated_mask(world), world))

    def fall(self):
        self.grid_y += 1
        self.angular_velocity += 0.5
        self.fall_distance += 1

    def slide(self, world):
        left = [(x - 1, y + 1) for x, y in self.get_rotated_mask(world)]
        right = [(x + 1, y + 1) for x, y in self.get_rotated_mask(world)]
        can_left = all(world.get(x, y) is None for x, y in left)
        can_right = all(world.get(x, y) is None for x, y in right)

        if can_left and not can_right:
            self.grid_x -= 1;
            self.grid_y += 1;
            self.angle -= 2.5
        elif can_right and not can_left:
            self.grid_x += 1;
            self.grid_y += 1;
            self.angle += 2.5
        elif can_left and can_right:
            if random.random() < 0.5:
                self.grid_x -= 1;
                self.grid_y += 1;
                self.angle -= 2.5
            else:
                self.grid_x += 1;
                self.grid_y += 1;
                self.angle += 2.5

    def ripple_displace_sand(self, x, y, world, max_chain=20):
        for dx in [-1, 1]:
            chain = []
            for i in range(max_chain):
                tx, ty = x + dx * i, y
                if world.in_bounds(tx, ty):
                    p = world.get(tx, ty)
                    if p and p.material and p.material.physics_type == (1, 0):
                        chain.append((tx, ty))
                    else:
                        break
            for tx, ty in reversed(chain):
                nx = tx + dx
                if world.in_bounds(nx, ty) and world.get(nx, ty) is None:
                    world.move(tx, ty, nx, ty, world.get(tx, ty))

    def crack_materials(self, world, bottom_cells):
        for x, y in bottom_cells:
            p = world.get(x, y)
            if not p:
                continue

            if p.type == "Твёрдый песок":
                world.set(x, y, Particle("Песок"))
                self.spawn_cracks(world, x, y, "Твёрдый песок")

            elif p.type == "Скала":
                if random.random() < 0.25:
                    world.set(x, y, Particle("Каменная крошка"))
                    self.spawn_cracks(world, x, y, "Скала")

            elif p.type == "Стекло":
                if random.random() < 0.25:
                    world.set(x, y, Particle("Осколки стекла"))
                    self.spawn_cracks(world, x, y, "Стекло")
                else:
                    world.set(x, y, None)
                    self.spawn_cracks(world, x, y, "Стекло")

    def apply_crack(self, world, x, y, target_type):
        if target_type == "Стекло":
            if random.random() < 0.25:
                world.set(x, y, Particle("Осколки стекла"))
            else:
                world.set(x, y, None)
        elif target_type == "Твёрдый песок":
            world.set(x, y, Particle("Песок"))
        elif target_type == "Скала":
            world.set(x, y, Particle("Каменная крошка"))

    def spawn_cracks(self, world, x, y, target_type):
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1),
                      (1, 1), (-1, 1), (1, -1), (-1, -1)]

        weighted_dirs = []
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if not world.in_bounds(nx, ny):
                continue
            p = world.get(nx, ny)
            if p and p.type == target_type:
                weighted_dirs.extend([(dx, dy)] * 3)
            elif p and p.type != "Камень":
                weighted_dirs.extend([(dx, dy)] * 2)
            elif p is None:
                weighted_dirs.append((dx, dy))

        if not weighted_dirs:
            return

        dx, dy = random.choice(weighted_dirs)
        length = random.randint(3, 5)
        cx, cy = x, y

        for _ in range(length):
            cx += dx
            cy += dy
            if not world.in_bounds(cx, cy):
                break
            p = world.get(cx, cy)
            if p and p.type == target_type:
                self.apply_crack(world, cx, cy, target_type)

        if random.random() < 0.25:
            if dx != 0:
                mirror_dx, mirror_dy = -dx, dy
            else:
                mirror_dx, mirror_dy = dx, -dy

            for _ in range(random.randint(3, 7)):
                cx += mirror_dx
                cy += mirror_dy
                if not world.in_bounds(cx, cy):
                    break
                p = world.get(cx, cy)
                if p and p.type == target_type:
                    self.apply_crack(world, cx, cy, target_type)

    def update_physics(self, world):
        if self.dragging: return

        for x, y in self.process_mask(self.get_rotated_mask(world), world):
            world.set(x, y, None)

        if not self.is_fully_within_bounds(world): return

        below = [(x, y + 1) for x, y in self.get_rotated_mask(world)]
        can_fall = all(0 <= y < world.height and world.get(x, y) is None for x, y in below)

        prev_falling = self.was_falling
        self.was_falling = can_fall

        if can_fall:
            self.fall()
        else:
            self.angular_velocity *= 0.8
            self.slide(world)

        just_landed = prev_falling and not can_fall
        if just_landed:
            wave_strength = min(1 + self.fall_distance // 2, 60)
            bottom = [(x, y + 1) for x, y in self.get_rotated_mask(world)]
            for x, y in bottom:
                if 0 <= x < world.width and 0 <= y < world.height:
                    p = world.get(x, y)
                    if p and p.material and p.material.physics_type == (1, 0):
                        self.ripple_displace_sand(x, y, world, max_chain=wave_strength)

            self.crack_materials(world, bottom)
            self.fall_distance = 0

        self.angle += self.angular_velocity

        for x, y in self.process_mask(self.get_rotated_mask(world), world):
            world.set(x, y, Particle("Камень"))

    def handle_event(self, event, pixel_size, world):
        def clamp_center(x, y):
            return max(3, min(x, world.width - 6)), max(3, min(y, world.height - 7))

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            mx, my = event.pos
            gx, gy = mx // pixel_size, my // pixel_size
            if (gx, gy) in self.process_mask(self.get_rotated_mask(world), world):
                for x, y in self.process_mask(self.get_rotated_mask(world), world):
                    world.set(x, y, None)
                self.dragging = True
                self.drag_offset = (gx - self.grid_x, gy - self.grid_y)
                self.preview_mask = []

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 3:
            self.dragging = False
            if hasattr(self, "preview_mask"):
                for x, y in self.preview_mask:
                    world.set(x, y, Particle("Камень"))
                del self.preview_mask

        elif event.type == pygame.MOUSEMOTION and self.dragging:
            mx, my = event.pos
            gx, gy = mx // pixel_size, my // pixel_size
            self.grid_x, self.grid_y = clamp_center(gx - self.drag_offset[0], gy - self.drag_offset[1])
            self.preview_mask = self.process_mask(self.get_rotated_mask(world), world)
