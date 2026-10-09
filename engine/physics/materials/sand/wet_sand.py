import random

from engine.physics.physics import get_gravity_vector, physics_rotation


def tick_wet_sand(world, x, y):
    particle = world.get(x, y)
    if not particle:
        return

    if hasattr(particle, "age") and particle.age > 0:
        particle.age += 1

    dx, dy = get_gravity_vector(physics_rotation)

    fall_distance = 2 if random.random() < 0.05 else 1
    tx = x + dx * fall_distance
    ty = y + dy * fall_distance

    if world.is_empty_or_liquid(tx, ty):
        world.move(x, y, tx, ty, particle)
        return

    side_dx = -dy
    side_dy = dx
    directions = []

    for side in [-1, 1]:
        sx = x + dx + side_dx * side
        sy = y + dy + side_dy * side
        if world.is_empty_or_liquid(sx, sy):
            directions.append((sx, sy))

    if directions:
        nx, ny = random.choice(directions)
        world.move(x, y, nx, ny, particle)