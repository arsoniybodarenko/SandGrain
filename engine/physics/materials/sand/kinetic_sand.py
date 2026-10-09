import random

from engine.physics.physics import get_gravity_vector, physics_rotation


def tick_kinetic_sand(world, x, y):
    particle = world.get(x, y)
    if not particle:
        return

    neighbors = 0
    for nx, ny in [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]:
        if world.in_bounds(nx, ny):
            neighbor = world.get(nx, ny)
            if neighbor and neighbor.type == "Кинетический песок":
                neighbors += 1

    stickiness = min(0.8, neighbors / 4.0)

    if random.random() < stickiness:
        return

    dx, dy = get_gravity_vector(physics_rotation)
    fall_distance = 2 if random.random() < 0.05 else 1
    tx = x + dx * fall_distance
    ty = y + dy * fall_distance

    if world.in_bounds(tx, ty):
        target = world.get(tx, ty)
        if target is None:
            world.set(tx, ty, particle)
            world.set(x, y, None)
            return
        elif target.material and target.material.physics_type[0] == 2:
            world.swap(x, y, tx, ty)
            return

    side_dx = -dy
    side_dy = dx
    directions = []

    for side in [-1, 1]:
        nx = x + side_dx * side + dx
        ny = y + side_dy * side + dy
        if world.in_bounds(nx, ny):
            target = world.get(nx, ny)
            if target is None or (target.material and target.material.physics_type[0] == 2):
                directions.append((nx, ny))

    if directions and random.random() < 0.05:
        nx, ny = random.choice(directions)
        target = world.get(nx, ny)
        if target is None:
            world.set(nx, ny, particle)
            world.set(x, y, None)
        else:
            world.swap(x, y, nx, ny)