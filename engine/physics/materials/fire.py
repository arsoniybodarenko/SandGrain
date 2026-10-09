import random


def tick_fire(world, x, y):
    p = world.get(x, y)
    if not p or not p.material:
        return

    p.age += 1
    lifespan = 25 + random.randint(-10, 10)

    if p.age < lifespan * 0.8:
        for dy in [1, 2]:
            ny = y - dy
            if ny < 0:
                continue

            dx = 0
            if random.random() < 0.1:
                dx = random.choice([-1, 1])

            nx = x + dx
            if 0 <= nx < world.width and world.get(nx, ny) is None:
                world.set(nx, ny, p)
                world.set(x, y, None)
                return

    progress = p.age / lifespan
    if p.material.name == "Огонь":
        p.color = (220, 100, 10)
        if progress <= 0.1:
            p.color = (250, 230, 120)
        elif progress <= 0.3:
            p.color = (230, 170, 60)

    if p.material.name == "Гиперогонь":
        p.color = (110, 20, 180)
        if progress <= 0.1:
            p.color = (220, 60, 140)
        elif progress <= 0.3:
            p.color = (160, 30, 150)

    if progress > 0.5:
        p.color = (45, 55, 70)

    if p.age >= lifespan:
        world.set(x, y, None)