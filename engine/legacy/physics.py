from particle import Particle
import time


def update_physics(world):
    for y in reversed(range(world.height)):
        for x in range(world.width):
            particle = world.get(x, y)
            if particle and not particle.updated:
                if particle.type == "Песок":
                    sand_physics(world, x, y)
                elif particle.type == "Вода":
                    water_physics(world, x, y)
                elif particle.type == "Мокрый песок":
                    wet_sand_physics(world, x, y)
                elif particle.type == "Твёрдый песок":
                    hard_sand_physics(world, x, y)
                particle.updated = True

    for row in reversed(world.grid):
        for p in row:
            if p:
                p.updated = False


import random


def nearest_air_distance(world, x, y, max_radius=3):
    for r in range(max_radius + 1):
        for dx in range(-r, r + 1):
            dy = r - abs(dx)
            for sign in [-1, 1]:
                nx, ny = x + dx, y + sign * dy
                if 0 <= nx < world.width and 0 <= ny < world.height:
                    if world.get(nx, ny) is None:
                        return r
    return None


def wet_sand_physics(world, x, y):
    particle = world.get(x, y)
    if not particle:
        return

    now = time.time()

    if world.get(x, y + 1) is None or world.get(x, y + 1):
        world.set(x, y + 1, particle)
        world.set(x, y, None)
        return

    directions = []
    if world.get(x - 1, y + 1) is None:
        directions.append((-1, 1))
    if world.get(x + 1, y + 1) is None:
        directions.append((1, 1))
    random.shuffle(directions)
    for dx, dy in directions:
        nx, ny = x + dx, y + dy
        if world.get(nx, ny) is None:
            world.set(nx, ny, particle)
            world.set(x, y, None)
            return

    if particle.flooded > 0:
        spread_dirs = [
            (0, 1), (0, 1), (0, 1),
            (1, 0), (1, 0),
            (-1, 0), (-1, 0),
            (1, 1), (-1, 1),
            (0, -1),
            (1, -1), (-1, -1)
        ]
        random.shuffle(spread_dirs)
        for dx, dy in spread_dirs:
            nx, ny = x + dx, y + dy
            neighbor = world.get(nx, ny)
            if neighbor and neighbor.type in ["Песок", "Мокрый песок"] and neighbor.flooded < 2:
                neighbor.flooded += 1
                neighbor.created_at = now
                particle.flooded -= 1
                break
            if neighbor is None and dy == 0:
                below = world.get(nx, ny + 1)
                if below and (
                        below.type not in ["Песок", "Мокрый песок", "Твёрдый песок"]
                        or (below.type == "Мокрый песок" and below.flooded == 2)
                ):
                    world.set(nx, ny, Particle("Вода"))
                    particle.flooded -= 1
                    break

    if particle.flooded == 0:
        if not hasattr(particle, "drying_started_at") or particle.drying_started_at is None:
            particle.drying_started_at = now
            return

        elapsed = now - particle.drying_started_at

        if elapsed < 120:
            return

        if not hasattr(particle, "air_distance") or now - getattr(particle, "last_air_check", 0) > 1:
            particle.air_distance = nearest_air_distance(world, x, y)
            particle.last_air_check = now

        if particle.air_distance is None or particle.air_distance > 3:
            particle.drying_started_at = None
            return

        dry_times = [10, 15, 30, 60]
        dry_time = dry_times[particle.air_distance]
        t = min(1.0, (elapsed - 120) / dry_time)

        if not hasattr(particle, "last_color_update") or now - particle.last_color_update > 0.2:
            particle.last_color_update = now
            wet = (169, 153, 103)
            dry = (219, 203, 153)
            r = int(wet[0] * (1 - t) + dry[0] * t)
            g = int(wet[1] * (1 - t) + dry[1] * t)
            b = int(wet[2] * (1 - t) + dry[2] * t)
            particle.color = (r, g, b)

        if (elapsed - 120) >= dry_time:
            particle.type = "Твёрдый песок"
            particle.color = (219, 203, 153)


def water_physics(world, x, y):
    below = (x, y + 1)
    down_left = (x - 1, y + 1)
    down_right = (x + 1, y + 1)
    left = (x - 1, y)
    right = (x + 1, y)

    if world.get(*below) is None:
        world.set(*below, world.get(x, y))
        world.set(x, y, None)
        return

    for dx, dy in [down_left, down_right]:
        if 0 <= dx < world.width and 0 <= dy < world.height and world.get(dx, dy) is None:
            world.set(dx, dy, world.get(x, y))
            world.set(x, y, None)
            return

    directions = [left, right]
    dx, dy = random.choice(directions)
    if 0 <= dx < world.width and 0 <= dy < world.height and world.get(dx, dy) is None:
        world.set(dx, dy, world.get(x, y))
        world.set(x, y, None)

    for dx, dy in [left, right, down_right, down_left, below]:
        p = world.get(dx, dy)
        if p and p.type in ["Песок", "Мокрый песок", "Твёрдый песок"] and p.flooded < 2:
            p.flooded += 1
            p.created_at = time.time()
            world.set(x, y, None)
            return


def hard_sand_physics(world, x, y):
    particle = world.get(x, y)
    if not particle:
        return

    now = time.time()

    if particle.flooded > 1:
        new_p = Particle("Мокрый песок")
        new_p.flooded = 1
        world.set(x, y, new_p)
        return

    spread_dirs = [
        (0, 1), (1, 0), (-1, 0),
        (1, 1), (-1, 1), (0, -1),
        (1, -1), (-1, -1)
    ]
    random.shuffle(spread_dirs)
    for dx, dy in spread_dirs:
        nx, ny = x + dx, y + dy
        if 0 <= nx < world.width and 0 <= ny < world.height:
            neighbor = world.get(nx, ny)
            if neighbor and neighbor.type in ["Мокрый песок"] and neighbor.flooded > 0:
                particle.flooded += 1
                neighbor.flooded -= 1
                particle.created_at = now
                break


def sand_physics(world, x, y):
    particle = world.get(x, y)
    if not particle:
        return

    if particle.flooded > 1:
        new_p = Particle("Мокрый песок")
        new_p.flooded = 1
        world.set(x, y, new_p)
        return

    fall_distance = random.choice([1, 2])
    if world.get(x, y + fall_distance) is None:
        world.set(x, y + fall_distance, particle)
        world.set(x, y, None)
        return

    if world.get(x, y + 1) is None:
        return

    directions = []

    if world.get(x - 1, y + 1) is None and world.get(x - 2, y + 1) is None:
        directions.append((-2, 1))
    elif world.get(x - 1, y + 1) is None:
        directions.append((-1, 1))

    if world.get(x + 1, y + 1) is None and world.get(x + 2, y + 1) is None:
        directions.append((2, 1))
    elif world.get(x + 1, y + 1) is None:
        directions.append((1, 1))

    random.shuffle(directions)

    for dx, dy in directions:
        nx, ny = x + dx, y + dy
        if world.get(nx, ny) is None:
            world.set(nx, ny, particle)
            world.set(x, y, None)
            return
