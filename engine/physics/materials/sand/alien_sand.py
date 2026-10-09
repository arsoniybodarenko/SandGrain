import random

from engine.physics.physics import get_gravity_vector, physics_rotation


def tick_alien_sand(world, x, y):
    particle = world.get(x, y)
    if not particle:
        return

    dx, dy = get_gravity_vector(physics_rotation)
    dx, dy = -dx, -dy

    fall_distance = random.choice([1, 2])
    tx = x + dx * fall_distance
    ty = y + dy * fall_distance
    if world.get(tx, ty) is None:
        world.set(tx, ty, particle)
        world.set(x, y, None)
        return

    tx = x + dx
    ty = y + dy
    if world.get(tx, ty) is None:
        return

    side_dx = -dy
    side_dy = dx

    directions = []

    lx1 = x + side_dx + dx
    ly1 = y + side_dy + dy
    lx2 = x + side_dx * 2 + dx
    ly2 = y + side_dy * 2 + dy
    if world.get(lx1, ly1) is None and world.get(lx2, ly2) is None:
        directions.append((side_dx * 2 + dx, side_dy * 2 + dy))
    elif world.get(lx1, ly1) is None:
        directions.append((side_dx + dx, side_dy + dy))

    rx1 = x - side_dx + dx
    ry1 = y - side_dy + dy
    rx2 = x - side_dx * 2 + dx
    ry2 = y - side_dy * 2 + dy
    if world.get(rx1, ry1) is None and world.get(rx2, ry2) is None:
        directions.append((-side_dx * 2 + dx, -side_dy * 2 + dy))
    elif world.get(rx1, ry1) is None:
        directions.append((-side_dx + dx, -side_dy + dy))

    if directions:
        ddx, ddy = random.choice(directions)
        nx = x + ddx
        ny = y + ddy
        if world.get(nx, ny) is None:
            world.set(nx, ny, particle)
            world.set(x, y, None)