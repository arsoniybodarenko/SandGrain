import math
import random

from .particle import Particle

CRACK_FRACTION = 0.35
BODY_BLAST = 0.6
CUSHION = 0.1
_DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1))


def shatter_cell(world, x, y):
    p = world.get(x, y)
    if p is None or p.material is None:
        return False
    mat = p.material
    if mat.shatter_to and random.random() < mat.shatter_chance:
        world.set(x, y, Particle(mat.shatter_to, temperature=p.temperature))
    else:
        world.set(x, y, None)
    return True


def break_cell(world, x, y, energy):
    p = world.get(x, y)
    if p is None or p.material is None:
        return False
    hardness = p.material.hardness
    if hardness is None or energy < hardness:
        return False
    type_name = p.type
    shatter_cell(world, x, y)
    spread_cracks(world, x, y, energy, type_name, hardness)
    return True


def spread_cracks(world, x, y, energy, type_name, hardness):
    weighted = []
    for dx, dy in _DIRECTIONS:
        nx, ny = x + dx, y + dy
        if not world.in_bounds(nx, ny):
            continue
        q = world.get(nx, ny)
        if q is not None and q.type == type_name:
            weighted.extend([(dx, dy)] * 3)
        elif q is not None and not world.is_border(nx, ny):
            weighted.extend([(dx, dy)] * 2)
        elif q is None:
            weighted.append((dx, dy))
    if not weighted:
        return

    ratio = min(4.0, energy / hardness)
    dx, dy = random.choice(weighted)
    length = random.randint(3, 5) + int(ratio)
    cx, cy, e = x, y, energy
    for _ in range(length):
        cx += dx
        cy += dy
        if not world.in_bounds(cx, cy):
            break
        e *= 0.8
        q = world.get(cx, cy)
        if q is not None and q.type == type_name and e >= hardness * CRACK_FRACTION:
            shatter_cell(world, cx, cy)

    if random.random() < 0.25 + 0.1 * min(2.0, ratio):
        mx, my = (-dx, dy) if dx != 0 else (dx, -dy)
        for _ in range(random.randint(3, 6)):
            cx += mx
            cy += my
            if not world.in_bounds(cx, cy):
                break
            e *= 0.8
            q = world.get(cx, cy)
            if q is not None and q.type == type_name and e >= hardness * CRACK_FRACTION:
                shatter_cell(world, cx, cy)


def shockwave(world, x, y, radius, strength, up=(0, -1)):
    grid = world.grid
    W = world.width
    H = world.height
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx == 0 and dy == 0:
                continue
            nx, ny = x + dx, y + dy
            if nx < 0 or nx >= W or ny < 0 or ny >= H:
                continue
            q = grid[ny][nx]
            if q is None or q.body is not None or q.vx or q.vy or q.material is None:
                continue
            if q.material.physics_type[0] not in (1, 2):
                continue
            dist = math.hypot(dx, dy)
            k = strength / dist
            q.vx += dx / dist * k + up[0] * 0.6 + random.uniform(-0.4, 0.4)
            q.vy += dy / dist * k + up[1] * 0.6 + random.uniform(-0.4, 0.4)


def apply_impact(world, pairs, energy, up=(0, -1)):
    if not pairs:
        return
    per_contact = energy / len(pairs)
    powder = None
    for bx, by, wx, wy in pairs:
        wp = world.get(wx, wy)
        soft = wp is not None and wp.material is not None and wp.material.physics_type[0] == 1
        if soft and powder is None:
            powder = (wx, wy)
        break_cell(world, wx, wy, per_contact)
        break_cell(world, bx, by, per_contact * (CUSHION if soft else 1.0))
    if powder is not None:
        radius = min(5, 2 + int(math.sqrt(energy) / 6))
        strength = min(2.4, 0.15 * math.sqrt(energy))
        if strength > 0.2:
            shockwave(world, powder[0], powder[1], radius, strength, up)


def explode(world, x, y, radius, power, fire=0.0, up=(0, -1)):
    grid = world.grid
    W = world.width
    H = world.height
    broken = []
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            d2 = dx * dx + dy * dy
            if d2 > radius * radius:
                continue
            nx, ny = x + dx, y + dy
            if nx < 0 or nx >= W or ny < 0 or ny >= H:
                continue
            dist = math.sqrt(d2)
            local = power * (1.0 - dist / (radius + 1.0))
            p = grid[ny][nx]
            if p is None:
                if fire and random.random() < fire * local / power:
                    world.set(nx, ny, Particle("Огонь"))
                continue
            mat = p.material
            if mat is None:
                continue
            if dist > 0:
                ux, uy = dx / dist, dy / dist
            else:
                angle = random.uniform(0.0, 2.0 * math.pi)
                ux, uy = math.cos(angle), math.sin(angle)
            if p.body is not None:
                f = local * BODY_BLAST
                p.body.apply_impulse(ux * f, uy * f, nx + 0.5, ny + 0.5)
            elif mat.physics_type[0] in (1, 2) and not (p.vx or p.vy):
                k = local * 0.45
                p.vx += ux * k + up[0] * 0.5
                p.vy += uy * k + up[1] * 0.5
            if mat.hardness is not None and local >= mat.hardness:
                broken.append((nx, ny, ux, uy, local))

    for nx, ny, ux, uy, local in broken:
        p = world.get(nx, ny)
        if p is None or p.material is None:
            continue
        mat = p.material
        if mat.shatter_to and random.random() < mat.shatter_chance:
            debris = Particle(mat.shatter_to, temperature=p.temperature)
            speed = min(2.5, 0.35 * local)
            debris.vx = ux * speed + random.uniform(-0.3, 0.3)
            debris.vy = uy * speed + random.uniform(-0.3, 0.3)
            world.set(nx, ny, debris)
        else:
            world.set(nx, ny, None)
