import random


def tick_gas(world, x, y):
    particle = world.get(x, y)
    if not particle:
        return

    for dy in [1, 2]:
        ny = y - dy
        if ny < 0:
            continue

        dx = 0
        if random.random() < 0.1:
            dx = random.choice([-1, 1])

        nx = x + dx

        if world.is_empty_or_liquid(nx, ny):
            world.move(x, y, nx, ny, particle)
            return