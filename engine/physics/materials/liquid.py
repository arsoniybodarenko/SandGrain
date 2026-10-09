import random


def tick_liquid(world, x, y):
    particle = world.get(x, y)
    if not particle:
        return

    a = random.choice((1, 2, 3))
    if a == 1:
        nx, ny = x - 1, y + 1
        if world.in_bounds(nx, ny) and world.get(nx, ny) is None:
            world.set(nx, ny, particle)
            world.set(x, y, None)
            return
    elif a == 2:
        nx, ny = x, y + 1
        if world.in_bounds(nx, ny) and world.get(nx, ny) is None:
            world.set(nx, ny, particle)
            world.set(x, y, None)
            return
    else:
        nx, ny = x + 1, y + 1
        if world.in_bounds(nx, ny) and world.get(nx, ny) is None:
            world.set(nx, ny, particle)
            world.set(x, y, None)
            return
    b = random.choice((0, 1, 2, 3, 4, 5))
    if b == 0:
        nx, ny = x - 1, y
    elif b == 1:
        nx, ny = x + 1, y
    elif b == 2:
        nx, ny = x + 2, y
    elif b == 3:
        nx, ny = x - 2, y
    elif b == 4:
        nx, ny = x - 3, y
    elif b == 5:
        nx, ny = x + 3, y

    if world.in_bounds(nx, ny) and world.get(nx, ny) is None:
        world.set(nx, ny, particle)
        world.set(x, y, None)