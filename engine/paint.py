import random
from .particle import Particle
from .materials import MATERIALS


def apply_fire_logic(world, nx, ny, mat):
    target_temp = mat.temperature
    heat_speed = 50

    particle = world.get(nx, ny)

    if not particle:
        world.set(nx, ny, Particle(mat.name))
        return

    if particle.type == "Творческая граница":
        return

    if particle.material.name in ("Огонь", "Гиперогонь"):
        world.set(nx, ny, Particle(mat.name))
        return

    if hasattr(particle, "temperature"):
        particle.temperature += heat_speed
        if particle.temperature > target_temp:
            particle.temperature = target_temp

    world.draw_cell(nx, ny)
    world.wake(nx, ny)


def draw_circle(world, cx, cy, selected_material, radius, erase=False, selected_color=None):
    mat = MATERIALS[selected_material]

    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            if dx * dx + dy * dy <= radius * radius:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < world.width and 0 <= ny < world.height:

                    existing = world.get(nx, ny)
                    if erase:
                        if existing and existing.type != "Творческая граница":
                            world.set(nx, ny, None)
                    else:
                        if selected_material in ("Огонь", "Гиперогонь"):
                            apply_fire_logic(world, nx, ny, mat)
                            continue
                        if not existing or existing.type != "Творческая граница":
                            world.set(nx, ny, Particle(selected_material, color=selected_color))


def draw_square(world, cx, cy, selected_material, radius, erase=False, selected_color=None):
    mat = MATERIALS[selected_material]

    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < world.width and 0 <= ny < world.height:

                if selected_material in ("Огонь", "Гиперогонь"):
                    apply_fire_logic(world, nx, ny, mat)
                    continue

                existing = world.get(nx, ny)
                if erase:
                    if existing and existing.type != "Творческая граница":
                        world.set(nx, ny, None)
                else:
                    if not existing or existing.type != "Творческая граница":
                        world.set(nx, ny, Particle(selected_material, color=selected_color))


def draw_random(world, cx, cy, selected_material, radius, erase=False, selected_color=None):
    mat = MATERIALS[selected_material]

    for _ in range(radius * radius):
        dx = random.randint(-radius, radius)
        dy = random.randint(-radius, radius)
        nx, ny = cx + dx, cy + dy

        if 0 <= nx < world.width and 0 <= ny < world.height:

            if selected_material in ("Огонь", "Гиперогонь"):
                apply_fire_logic(world, nx, ny, mat)
                continue

            existing = world.get(nx, ny)
            if erase:
                if existing and existing.type != "Творческая граница":
                    world.set(nx, ny, None)
            else:
                if not existing or existing.type != "Творческая граница":
                    world.set(nx, ny, Particle(selected_material, color=selected_color))


def draw_pencil(world, cx, cy, radius, selected_color):
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            if dx * dx + dy * dy <= radius * radius:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < world.width and 0 <= ny < world.height:
                    particle = world.get(nx, ny)
                    if particle and particle.material and particle.material.paintable:
                        particle.color = selected_color
                        world.draw_cell(nx, ny)


def apply_brush(world, x, y, selected_material, radius, erase, brush_type, selected_color=None):
    mat = MATERIALS[selected_material]
    tint = selected_color if mat.paintable else None

    if brush_type == "Карандаш":
        draw_pencil(world, x, y, radius, selected_color)
        return

    if brush_type == "Ластик":
        draw_circle(world, x, y, selected_material, radius, erase=True)
        return

    if brush_type == "Круглая кисть":
        draw_circle(world, x, y, selected_material, radius, erase, tint)
    elif brush_type == "Квадратная кисть":
        draw_square(world, x, y, selected_material, radius, erase, tint)
    elif brush_type == "Случайная кисть":
        draw_random(world, x, y, selected_material, radius, erase, tint)


def draw_line(world, x0, y0, x1, y1, selected_material, radius, erase=False, brush_type="Круглая кисть",
              selected_color=None):
    dx = x1 - x0
    dy = y1 - y0
    steps = max(abs(dx), abs(dy))
    if steps == 0:
        apply_brush(world, x0, y0, selected_material, radius, erase, brush_type, selected_color)
        return
    for i in range(steps + 1):
        t = i / steps
        x = int(round(x0 + dx * t))
        y = int(round(y0 + dy * t))
        apply_brush(world, x, y, selected_material, radius, erase, brush_type, selected_color)
