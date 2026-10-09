import random

from engine.physics.physics import get_gravity_vector, physics_rotation


def tick_sand(world, x, y):
    particle = world.get(x, y)
    if not particle:
        return

    dx, dy = get_gravity_vector(physics_rotation)

    fall_distance = random.choice([1, 2])
    tx = x + dx * fall_distance
    ty = y + dy * fall_distance
    if world.is_empty_or_liquid(tx, ty):
        world.move(x, y, tx, ty, particle)
        return

    tx = x + dx
    ty = y + dy
    if world.is_empty_or_liquid(tx, ty):
        return

    side_dx = -dy
    side_dy = dx

    directions = []

    lx1 = x + side_dx + dx
    ly1 = y + side_dy + dy
    lx2 = x + side_dx * 2 + dx
    ly2 = y + side_dy * 2 + dy
    if world.is_empty_or_liquid(lx1, ly1) and world.is_empty_or_liquid(lx2, ly2):
        directions.append((side_dx * 2 + dx, side_dy * 2 + dy))
    elif world.is_empty_or_liquid(lx1, ly1):
        directions.append((side_dx + dx, side_dy + dy))

    rx1 = x - side_dx + dx
    ry1 = y - side_dy + dy
    rx2 = x - side_dx * 2 + dx
    ry2 = y - side_dy * 2 + dy
    if world.is_empty_or_liquid(rx1, ry1) and world.is_empty_or_liquid(rx2, ry2):
        directions.append((-side_dx * 2 + dx, -side_dy * 2 + dy))
    elif world.is_empty_or_liquid(rx1, ry1):
        directions.append((-side_dx + dx, -side_dy + dy))

    if directions:
        ddx, ddy = random.choice(directions)
        nx = x + ddx
        ny = y + ddy
        if world.is_empty_or_liquid(nx, ny):
            world.move(x, y, nx, ny, particle)
