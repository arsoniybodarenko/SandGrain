# physics.py
import math
import random
from engine.materials import MATERIALS
from engine.world import *
from concurrent.futures import ThreadPoolExecutor

physics_rotation = 0.0


def update_physics(world, x, y):
    particle = world.get(x, y)
    if not particle or particle.updated or not particle.material:
        return

    if handle_phase_transition(world, x, y):
        return

    handle_reactions(world, x, y)
    handle_burning(world, x, y)
    global_update(world, x, y)

    ptype, subtype = particle.material.physics_type
    if ptype == 0:
        particle.updated = True
        return

    if ptype == 1:
        if subtype == 0:
            powder_physics(world, x, y)
        elif subtype == 1:
            wet_powder_physics(world, x, y)
        elif subtype == 2:
            alien_powder_physics(world, x, y)
        elif subtype == 3:
            kinetic_sand_physics(world, x, y)
        elif subtype == 4:
            clay_physics(world, x, y)
        # elif subtype == 4:
        #    clay_physics(world, x, y)
    # elif ptype == "Твердое":
    #    solid_physics(world, x, y)
    elif ptype == 2:
        liquid_physics(world, x, y)
    elif ptype == 3:
        gas_physics(world, x, y)
    elif ptype == 4:
        update_fire_physics(world, x, y)

    particle.updated = True


def handle_burning(world, x, y):
    particle = world.get(x, y)
    if not particle or not particle.material:
        return

    mat = particle.material

    if not mat.flammable:
        return

    if hasattr(particle, "temperature") and hasattr(mat, "ignition_point"):
        if particle.temperature >= mat.ignition_point:
            particle.burning = True

    if not particle.burning:
        for nx, ny in [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]:
            neighbor = world.get(nx, ny)
            if neighbor and neighbor.material and neighbor.material.name in ("Огонь", "Гиперогонь"):
                particle.burning = True
                break

    if not particle.burning:
        return

    chance_self, chance_spread, chance_air = (mat.burn + (0, 0, 0))[:3]

    if random.random() < chance_self:
        world.set(x, y, Particle("Огонь"))
        return

    if random.random() < chance_spread:
        neighbors = [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]
        nx, ny = random.choice(neighbors)
        if world.in_bounds(nx, ny):
            target = world.get(nx, ny)
            if target is None:
                world.set(nx, ny, Particle("Огонь"))
            elif target.material and target.material.flammable:
                target.burning = True

    if random.random() < chance_air:
        air_cells = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if world.in_bounds(nx, ny) and world.get(nx, ny) is None:
                air_cells.append((nx, ny))

        if air_cells:
            nx, ny = random.choice(air_cells)
            world.set(nx, ny, Particle("Огонь"))


def global_update(world, x, y):
    particle = world.get(x, y)
    if not particle:
        return

    neighbor_coords = [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]
    neighbors = [(nx, ny, world.get(nx, ny)) for nx, ny in neighbor_coords]

    if particle.type == "Песок":
        for nx, ny, neighbor in neighbors:
            if neighbor and neighbor.type == "Вода":
                new_p = Particle("Мокрый песок")
                new_p.flooded = 1
                new_p.age = 1
                world.set(x, y, new_p)
                world.set(nx, ny, None)
                return
        if particle.flooded > 0:
            new_p = Particle("Мокрый песок")
            new_p.flooded = particle.flooded
            new_p.age = 1
            world.set(x, y, new_p)
            return

    elif particle.type == "Твёрдый песок":
        for nx, ny, neighbor in neighbors:
            if neighbor and neighbor.type == "Вода":
                new_p = Particle("Мокрый песок")
                new_p.flooded = 1
                new_p.age = 1
                world.set(x, y, new_p)
                world.set(nx, ny, None)
                return

    elif particle.type == "Мокрый песок":
        for nx, ny, neighbor in neighbors:
            if neighbor and neighbor.type == "Вода" and particle.flooded < 2:
                particle.flooded += 1
                world.set(nx, ny, None)
                return

        if particle.flooded == 0 and particle.age > 500:
            for nx, ny, neighbor in neighbors:
                if neighbor is None and random.random() < 0.01:
                    world.set(x, y, Particle("Песок"))
                    return

        if particle.age > 500:
            for nx, ny, neighbor in neighbors:
                if neighbor is None and random.random() < 0.005:
                    world.set(x, y, Particle("Твёрдый песок"))
                    return

        if particle.flooded == 2:
            spread_dirs = [(0, 1), (1, 0), (-1, 0), (1, 1), (-1, 1), (0, -1), (1, -1), (-1, -1)]
            dx, dy = spread_dirs[random.randrange(len(spread_dirs))]
            nx, ny = x + dx, y + dy
            neighbor = world.get(nx, ny)

            if neighbor and neighbor.type == "Песок" and neighbor.flooded < 2:
                new_p = Particle("Мокрый песок")
                new_p.flooded = neighbor.flooded + 1
                new_p.age = 1
                world.set(nx, ny, new_p)
                particle.flooded = max(0, particle.flooded - 1)
                return

            elif neighbor and neighbor.type == "Твёрдый песок" and neighbor.flooded < 2:
                new_p = Particle("Мокрый песок")
                new_p.flooded = neighbor.flooded + 1
                new_p.age = 1
                world.set(nx, ny, new_p)
                particle.flooded = max(0, particle.flooded - 1)
                return

            elif neighbor and neighbor.type == "Мокрый песок" and neighbor.flooded < 2:
                neighbor.flooded += 1
                particle.flooded = max(0, particle.flooded - 1)
                return


def tick_physics(world):
    if physics_rotation == 180:
        y_range = range(world.height)
    else:
        y_range = reversed(range(world.height))

    for y in y_range:
        for x in range(world.width):
            spread_temperature(world, x, y)
            update_physics(world, x, y)

    for row in world.grid:
        for p in row:
            if p:
                p.updated = False


def update_chunk(world, y_start, y_end):
    for y in range(y_start, y_end):
        for x in range(world.width):
            spread_temperature(world, x, y)
            update_physics(world, x, y)


# def tick_physics(world, num_workers=4):
#    chunk_size = world.height // num_workers
#    with ThreadPoolExecutor(max_workers=num_workers) as executor:
#        futures = []
#        for i in range(num_workers):
#            y_start = i * chunk_size
#            y_end = (i+1) * chunk_size
#            futures.append(executor.submit(update_chunk, world, y_start, y_end))
#        for f in futures:
#            f.result()
#
#    for row in world.grid:
#        for p in row:
#            if p:
#                p.updated = False

def get_gravity_vector(physics_rotation):
    angle_rad = math.radians(physics_rotation)
    dx = round(math.sin(angle_rad))
    dy = round(math.cos(angle_rad))
    return dx, dy


def spread_temperature(world, x, y):
    p = world.get(x, y)
    if not p or not p.material or p.temperature is None:
        return

    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx == 0 and dy == 0:
                continue
            nx, ny = x + dx, y + dy
            neighbor = world.get(nx, ny)
            if not neighbor or not neighbor.material or neighbor.temperature is None:
                continue

            c1 = p.material.heat_capacity
            c2 = neighbor.material.heat_capacity
            if c1 == 0 or c2 == 0:
                continue

            t1 = p.temperature
            t2 = neighbor.temperature

            if abs(t1 - t2) < 0.1:
                continue

            k = min(p.material.conduct_heat, neighbor.material.conduct_heat)
            mix = (t1 * c1 + t2 * c2) / (c1 + c2)

            p.temperature += (mix - t1) * k
            neighbor.temperature += (mix - t2) * k


def handle_reactions(world, x, y):
    particle = world.get(x, y)
    if not particle or not particle.material or not particle.material.reacts_with:
        return

    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx == 0 and dy == 0:
                continue
            nx, ny = x + dx, y + dy
            if 0 <= nx < world.width and 0 <= ny < world.height:
                neighbor = world.get(nx, ny)
                if neighbor and neighbor.type in particle.material.reacts_with:
                    func_name = particle.material.reacts_with[neighbor.type]
                    reaction_func = globals().get(func_name)
                    if callable(reaction_func):
                        reaction_func(world, x, y, nx, ny)


def handle_phase_transition(world, x, y):
    particle = world.get(x, y)
    if not particle or not particle.material:
        return False

    mat = particle.material
    temp = particle.temperature
    new_type = None

    if mat.freezing_point is not None and temp <= mat.freezing_point:
        if mat.become_to and len(mat.become_to) > 0:
            new_type = mat.become_to[0]

    elif mat.boiling_point is not None and temp >= mat.boiling_point:
        if mat.become_to and len(mat.become_to) > 1:
            new_type = mat.become_to[1]

    elif mat.meltable and mat.melting_point is not None and temp >= mat.melting_point:
        if mat.become_to and len(mat.become_to) > 0:
            new_type = mat.become_to[0]

    elif mat.freezable and mat.freezing_point is not None and temp <= mat.freezing_point:
        if mat.become_to and len(mat.become_to) > 0:
            new_type = mat.become_to[0]

    if new_type and new_type in MATERIALS:
        new_mat = MATERIALS[new_type]
        new_particle = Particle(new_type, color=new_mat.color, temperature=temp)
        world.set(x, y, new_particle)
        return True

    return False


def powder_physics(world, x, y):
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


def clay_physics(world, x, y):
    particle = world.get(x, y)
    if not particle:
        return

    dx, dy = get_gravity_vector(physics_rotation)

    fall_distance = 1
    tx = x + dx * fall_distance
    ty = y + dy * fall_distance
    if world.is_empty_or_liquid(tx, ty):
        world.move(x, y, tx, ty, particle)
        return

    if world.is_empty_or_liquid(tx, ty):
        return


def wet_powder_physics(world, x, y):
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


def kinetic_sand_physics(world, x, y):
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


def alien_powder_physics(world, x, y):
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


def liquid_physics(world, x, y):
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


def solid_physics(world, x, y):
    pass


def gas_physics(world, x, y):
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


def update_fire_physics(world, x, y):
    p = world.get(x, y)
    if not p or not p.material:
        return

    p.age += 1
    lifespan = p.max_age

    progress = p.age / lifespan

    if p.material.name == "Огонь":
        if progress <= 0.1:
            p.color = (250, 230, 120)
        elif progress <= 0.3:
            p.color = (230, 170, 60)
        elif progress <= 0.5:
            p.color = (220, 100, 10)
        else:
            p.color = (45, 55, 70)

    if p.material.name == "Гиперогонь":
        if progress <= 0.1:
            p.color = (220, 60, 140)
        elif progress <= 0.3:
            p.color = (160, 30, 150)
        elif progress <= 0.5:
            p.color = (110, 20, 180)
        else:
            p.color = (45, 55, 70)

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

    if p.age >= lifespan:
        world.set(x, y, None)
