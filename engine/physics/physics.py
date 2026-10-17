import math
import random
from engine.materials import MATERIALS
from engine.world import *
from engine import damage
from engine.settings import SETTINGS

physics_rotation = 0.0

_tick = 0
_GLOBAL_TYPES = frozenset(("Песок", "Твёрдый песок", "Мокрый песок"))
_flags_cache = {}


def _material_flags(mat):
    flags = _flags_cache.get(mat)
    if flags is None:
        has_phase = (
            mat.freezing_point is not None
            or mat.boiling_point is not None
            or mat.melting_point is not None
        )
        low = mat.freezing_point if mat.freezing_point is not None else float("-inf")
        highs = []
        if mat.boiling_point is not None:
            highs.append(mat.boiling_point)
        if mat.meltable and mat.melting_point is not None:
            highs.append(mat.melting_point)
        high = min(highs) if highs else float("inf")
        flags = (has_phase, bool(mat.reacts_with), bool(mat.flammable), low, high)
        _flags_cache[mat] = flags
    return flags


def _free(grid, W, H, x, y):
    if x < 0 or x >= W or y < 0 or y >= H:
        return False
    t = grid[y][x]
    if t is None:
        return True
    m = t.material
    return m is None or m.physics_type[0] == 2


def _is_none(grid, W, H, x, y):
    return 0 <= x < W and 0 <= y < H and grid[y][x] is None


def _cell(grid, W, H, x, y):
    if x < 0 or x >= W or y < 0 or y >= H:
        return None
    return grid[y][x]


def _keep_awake(world, x, y):
    awake = world.chunk_awake
    for i in world.wake_targets[y][x]:
        awake[i] = AWAKE_TICKS


def update_physics(world, x, y):
    particle = world.grid[y][x]
    if particle is None or particle.updated == _tick:
        return
    mat = particle.material
    if mat is None:
        return

    ptype, subtype = mat.physics_type
    has_phase, has_reactions, flammable, phase_low, phase_high = _material_flags(mat)
    if has_phase:
        t = particle.temperature
        has_phase = t <= phase_low or t >= phase_high or particle.phase_energy > 0.0

    if (ptype == 0 and not (has_phase or has_reactions or flammable)
            and particle.type not in _GLOBAL_TYPES and not (particle.vx or particle.vy)):
        return

    if has_phase and handle_phase_transition(world, x, y):
        return

    if has_reactions:
        handle_reactions(world, x, y)
    if flammable:
        handle_burning(world, x, y)
    if particle.type in _GLOBAL_TYPES:
        global_update(world, x, y)

    if particle.vx or particle.vy:
        if grid_particle_is(world, x, y, particle):
            ballistic_step(world, x, y)
        particle.updated = _tick
        return

    if particle.body is not None:
        particle.updated = _tick
        return

    if ptype == 0:
        particle.updated = _tick
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
    elif ptype == 2:
        liquid_physics(world, x, y)
    elif ptype == 3:
        gas_physics(world, x, y)
    elif ptype == 4:
        update_fire_physics(world, x, y)

    particle.updated = _tick


def _blocks(t):
    return t is not None and (t.body is not None or t.material is None or t.material.physics_type[0] in (0, 1))


def _diag_ok(grid, W, H, x, y, tx, ty):
    if not _CORNER:
        return True
    return not (_blocks(_cell(grid, W, H, tx, y)) and _blocks(_cell(grid, W, H, x, ty)))


def _fall_run(world, grid, W, H, x, y, gx, gy, steps, free):
    moved = 0
    cx, cy = x, y
    for _ in range(steps):
        nx, ny = cx + gx, cy + gy
        if not free(grid, W, H, nx, ny):
            break
        world.move_to(cx, cy, nx, ny)
        cx, cy = nx, ny
        moved += 1
    return moved


def _accelerate(particle):
    particle.fall = min(particle.fall + _FALL_ACCEL, _FALL_TERMINAL)


def _is_liquid_cell(grid, W, H, x, y):
    t = _cell(grid, W, H, x, y)
    return t is not None and t.body is None and t.material is not None and t.material.physics_type[0] == 2


def _ceiling_above(world, x, y):
    gx, gy = get_gravity_vector(physics_rotation)
    ux, uy = x - gx, y - gy
    if not (0 <= ux < world.width and 0 <= uy < world.height):
        return True
    t = world.grid[uy][ux]
    return t is not None and (t.body is not None or (t.material is not None and t.material.physics_type[0] in (0, 1)))


def grid_particle_is(world, x, y, particle):
    return world.grid[y][x] is particle

_PH = SETTINGS.physics
_BALLISTIC_G = _PH.ballistic_gravity
_BALLISTIC_MAX = _PH.ballistic_max_speed
_BOUNCE = _PH.bounce
_LIQUID_BOUNCE = _PH.liquid_bounce
_LIQUID_BOUNCE_BURN = _PH.liquid_bounce_burn_chance
_STOP_SPEED = _PH.ballistic_stop_speed
_FLUID_DRAG = _PH.fluid_drag
_FALL_ACCEL = _PH.fall_acceleration
_FALL_TERMINAL = _PH.fall_terminal_speed
_CORNER = _PH.prevent_corner_cutting
_THERMAL_INTERVAL = SETTINGS.world.thermal_interval
_AMBIENT = SETTINGS.world.ambient_temperature
_THERMAL_THRESHOLD = SETTINGS.world.thermal_threshold
_K_PASSES = 2 * _THERMAL_INTERVAL
_PASSABLE_TYPES = (2, 3, 4)


def _passable(grid, W, H, x, y):
    if x < 0 or x >= W or y < 0 or y >= H:
        return False
    t = grid[y][x]
    if t is None:
        return True
    m = t.material
    return t.body is None and m is not None and m.physics_type[0] in _PASSABLE_TYPES


def ballistic_step(world, x, y):
    grid = world.grid
    p = grid[y][x]
    W = world.width
    H = world.height

    gdx, gdy = get_gravity_vector(physics_rotation)
    bounce_liquid = p.material is not None and p.material.liquid_bounce
    p.vx += gdx * _BALLISTIC_G
    p.vy += gdy * _BALLISTIC_G
    speed = math.hypot(p.vx, p.vy)
    if speed > _BALLISTIC_MAX:
        p.vx *= _BALLISTIC_MAX / speed
        p.vy *= _BALLISTIC_MAX / speed

    px = p.fx + p.vx
    py = p.fy + p.vy
    mx = int(px)
    my = int(py)
    p.fx = px - mx
    p.fy = py - my

    steps = max(abs(mx), abs(my))
    cx, cy = x, y
    for i in range(1, steps + 1):
        tx = x + int(math.floor(mx * i / steps + 0.5))
        ty = y + int(math.floor(my * i / steps + 0.5))
        if tx == cx and ty == cy:
            continue

        if (bounce_liquid and (p.vx * gdx + p.vy * gdy) > 0
                and _is_liquid_cell(grid, W, H, tx, ty)
                and not _is_liquid_cell(grid, W, H, tx - gdx, ty - gdy)):
            along = p.vx * gdx + p.vy * gdy
            p.vx -= (1.0 + _LIQUID_BOUNCE) * along * gdx
            p.vy -= (1.0 + _LIQUID_BOUNCE) * along * gdy
            p.fx = p.fy = 0.0
            handler = _IMPACT_HANDLERS.get(p.material.impact) if p.material.impact else None
            if handler is not None and (random.random() < _LIQUID_BOUNCE_BURN
                                        or abs(p.vx) + abs(p.vy) < _STOP_SPEED):
                handler(world, cx, cy, p)
                return
            break

        if _passable(grid, W, H, tx, ty):
            if grid[ty][tx] is not None:
                p.vx *= _FLUID_DRAG
                p.vy *= _FLUID_DRAG
            world.move_to(cx, cy, tx, ty)
            cx, cy = tx, ty
            continue

        impact = p.material.impact if p.material is not None else None
        handler = _IMPACT_HANDLERS.get(impact) if impact else None
        if handler is not None:
            handler(world, cx, cy, p)
            return

        block_x = tx != cx and not _passable(grid, W, H, tx, cy)
        block_y = ty != cy and not _passable(grid, W, H, cx, ty)
        if block_x == block_y:
            p.vx *= -_BOUNCE
            p.vy *= -_BOUNCE
        elif block_x:
            p.vx *= -_BOUNCE
        else:
            p.vy *= -_BOUNCE
        p.fx = p.fy = 0.0
        if abs(p.vx) + abs(p.vy) < _STOP_SPEED:
            p.vx = p.vy = 0.0
        break

    if p.vx or p.vy:
        _keep_awake(world, cx, cy)





def _impact_burn_out(world, x, y, particle):
    grid = world.grid
    W = world.width
    H = world.height
    free = [(x + dx, y + dy) for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))
            if _is_none(grid, W, H, x + dx, y + dy)]
    world.set(x, y, None)
    if free:
        fx, fy = random.choice(free)
        world.set(fx, fy, Particle("Огонь"))


_IMPACT_HANDLERS = {"burn_out": _impact_burn_out}


def burning_water_reaction(world, x, y, nx, ny):
    grid = world.grid
    sodium = grid[y][x]
    water = grid[ny][nx]
    if sodium is None or water is None or sodium.vx or sodium.vy:
        return
    if random.random() > _PH.sodium_reaction_chance:
        return

    gx, gy = get_gravity_vector(physics_rotation)
    world.set(nx, ny, Particle("Пар", temperature=_PH.sodium_steam_temperature))

    if sodium.body is not None:
        sodium.body.remove_particle(sodium)
    sodium.burning = True
    sodium.temperature = max(sodium.temperature, _PH.sodium_burning_temperature)

    angle = random.uniform(0.0, 2.0 * math.pi)
    speed = random.uniform(_PH.sodium_eject_speed_min, _PH.sodium_eject_speed_max)
    sodium.vx = math.cos(angle) * speed - gx
    sodium.vy = math.sin(angle) * speed - gy

    free = [(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
            if (dx or dy) and _is_none(grid, world.width, world.height, x + dx, y + dy)]
    if free and random.random() < _PH.sodium_flash_chance:
        fx, fy = random.choice(free)
        world.set(fx, fy, Particle("Огонь"))

    damage.explode(world, x, y, _PH.sodium_explosion_radius, _PH.sodium_explosion_power, up=(-gx, -gy))


def handle_burning(world, x, y):
    grid = world.grid
    particle = grid[y][x]
    if not particle or not particle.material:
        return

    mat = particle.material
    if not mat.flammable:
        return

    W = world.width
    H = world.height
    neighbors = ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))

    for nx, ny in neighbors:
        n = _cell(grid, W, H, nx, ny)
        if n is not None and n.material is not None and n.material.extinguishes:
            particle.burning = False
            if mat.ignition_point is not None and particle.temperature >= mat.ignition_point:
                particle.temperature = mat.ignition_point - _PH.extinguish_cooling_margin
            return

    if mat.ignition_point is not None and particle.temperature >= mat.ignition_point:
        particle.burning = True

    if not particle.burning:
        for nx, ny in neighbors:
            neighbor = _cell(grid, W, H, nx, ny)
            if neighbor and neighbor.material and neighbor.material.name in ("Огонь", "Гиперогонь"):
                particle.burning = True
                break

    if not particle.burning:
        return

    _keep_awake(world, x, y)

    chance_self, chance_spread, chance_air, chance_ash = (mat.burn + (0, 0, 0, 0))[:4]

    if random.random() < chance_self:
        if chance_ash and random.random() < chance_ash:
            world.set(x, y, Particle("Пепел", temperature=particle.temperature))
        else:
            world.set(x, y, Particle("Огонь"))
        return

    if random.random() < chance_spread:
        nx, ny = random.choice(neighbors)
        if world.in_bounds(nx, ny):
            target = grid[ny][nx]
            if target is None:
                world.set(nx, ny, Particle("Огонь"))
            elif target.material and target.material.flammable:
                target.burning = True

    if random.random() < chance_air:
        air_cells = [(nx, ny) for nx, ny in neighbors if _is_none(grid, W, H, nx, ny)]
        if air_cells:
            nx, ny = random.choice(air_cells)
            world.set(nx, ny, Particle("Огонь"))


def global_update(world, x, y):
    grid = world.grid
    W = world.width
    H = world.height
    particle = grid[y][x]
    if not particle:
        return

    neighbors = [
        (nx, ny, _cell(grid, W, H, nx, ny))
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
    ]

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

        if particle.flooded == 0 and particle.age > _PH.wet_sand_dry_age:
            for nx, ny, neighbor in neighbors:
                if neighbor is None and random.random() < _PH.wet_sand_dry_chance:
                    world.set(x, y, Particle("Песок"))
                    return

        if particle.age > _PH.wet_sand_dry_age:
            for nx, ny, neighbor in neighbors:
                if neighbor is None and random.random() < _PH.wet_sand_harden_chance:
                    world.set(x, y, Particle("Твёрдый песок"))
                    return

        if particle.flooded == 2:
            spread_dirs = [(0, 1), (1, 0), (-1, 0), (1, 1), (-1, 1), (0, -1), (1, -1), (-1, -1)]
            dx, dy = spread_dirs[random.randrange(len(spread_dirs))]
            nx, ny = x + dx, y + dy
            neighbor = _cell(grid, W, H, nx, ny)

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


_last_rotation = 0.0


def tick_physics(world):
    global _tick, _last_rotation
    _tick += 1
    world.tick_count += 1

    if physics_rotation != _last_rotation or not world.sleep_enabled:
        _last_rotation = physics_rotation
        world.wake_all()

    gdx, gdy = get_gravity_vector(physics_rotation)
    grid = world.grid
    width = world.width
    height = world.height
    awake = world.chunk_awake
    chunks_x = world.chunks_x

    if gdx == 0:
        y_range = range(height) if gdy < 0 else reversed(range(height))
        for y in y_range:
            row = grid[y]
            chunk_row = (y // CHUNK_SIZE) * chunks_x
            for cx in range(chunks_x):
                if awake[chunk_row + cx] <= 0:
                    continue
                x0 = cx * CHUNK_SIZE
                x1 = min(width, x0 + CHUNK_SIZE)
                for x in range(x0, x1):
                    if row[x] is None:
                        continue
                    update_physics(world, x, y)
    else:
        x_range = reversed(range(width)) if gdx > 0 else range(width)
        chunks_y = world.chunks_y
        for x in x_range:
            cx = x // CHUNK_SIZE
            for cy in range(chunks_y):
                if awake[cy * chunks_x + cx] <= 0:
                    continue
                y0 = cy * CHUNK_SIZE
                y1 = min(height, y0 + CHUNK_SIZE)
                for y in range(y0, y1):
                    if grid[y][x] is None:
                        continue
                    update_physics(world, x, y)

    thermal_pass(world)

    awake = world.chunk_awake
    for i in range(len(awake)):
        if awake[i] > 0:
            awake[i] -= 1


def update_chunk(world, y_start, y_end):
    for y in range(y_start, y_end):
        for x in range(world.width):
            update_physics(world, x, y)


_gravity_cache = {}


def get_gravity_vector(physics_rotation):
    vector = _gravity_cache.get(physics_rotation)
    if vector is None:
        angle_rad = math.radians(physics_rotation)
        vector = (round(math.sin(angle_rad)), round(math.cos(angle_rad)))
        _gravity_cache[physics_rotation] = vector
    return vector

_HEAT_NEIGHBOURS = ((1, 0), (0, 1), (1, 1), (-1, 1))


def spread_temperature(world, x, y):
    grid = world.grid
    p = grid[y][x]
    if p is None:
        return False
    mat = p.material
    if mat is None:
        return False
    c1 = mat.heat_capacity
    if c1 == 0:
        return False

    width = world.width
    height = world.height
    transferred = False
    for dx, dy in _HEAT_NEIGHBOURS:
        nx = x + dx
        ny = y + dy
        if nx < 0 or nx >= width or ny >= height:
            continue
        n = grid[ny][nx]
        if n is None:
            continue
        nmat = n.material
        if nmat is None:
            continue

        t1 = p.temperature
        t2 = n.temperature
        diff = t1 - t2
        if -_THERMAL_THRESHOLD < diff < _THERMAL_THRESHOLD:
            continue

        pt = mat.physics_type[0]
        nt = nmat.physics_type[0]
        if (pt == 4 and (nt == 2 or nt == 3)) or (nt == 4 and (pt == 2 or pt == 3)):
            continue

        c2 = nmat.heat_capacity
        if c2 == 0:
            continue

        k = min(mat.conduct_heat, nmat.conduct_heat, 1.0)
        if k <= 0:
            continue
        k = 1.0 - (1.0 - k) ** _K_PASSES

        mix = (t1 * c1 + t2 * c2) / (c1 + c2)
        p.temperature = t1 + (mix - t1) * k
        n.temperature = t2 + (mix - t2) * k
        transferred = True

        awake = world.chunk_awake
        for i in world.wake_targets[y][x]:
            awake[i] = AWAKE_TICKS
        for i in world.wake_targets[ny][nx]:
            awake[i] = AWAKE_TICKS
        ttl = world.thermal_ttl
        for i in world.thermal_targets[y][x]:
            ttl[i] = THERMAL_TTL
        for i in world.thermal_targets[ny][nx]:
            ttl[i] = THERMAL_TTL
    return transferred


def thermal_pass(world):
    if _THERMAL_INTERVAL > 1 and _tick % _THERMAL_INTERVAL:
        return
    ttl = world.thermal_ttl
    hot = world.thermal_hot
    grid = world.grid
    chunks_x = world.chunks_x
    width = world.width
    height = world.height
    for cy in range(world.chunks_y):
        for cx in range(chunks_x):
            ci = cy * chunks_x + cx
            if ttl[ci] <= 0:
                continue
            x0 = cx * CHUNK_SIZE
            x1 = min(width, x0 + CHUNK_SIZE)
            y0 = cy * CHUNK_SIZE
            y1 = min(height, y0 + CHUNK_SIZE)
            non_ambient = False
            for y in range(y0, y1):
                row = grid[y]
                for x in range(x0, x1):
                    p = row[x]
                    if p is None:
                        continue
                    if not non_ambient and abs(p.temperature - _AMBIENT) > _THERMAL_THRESHOLD:
                        non_ambient = True
                    spread_temperature(world, x, y)
            hot[ci] = non_ambient
    for i in range(len(ttl)):
        if ttl[i] > 0:
            ttl[i] -= 1


def handle_reactions(world, x, y):
    grid = world.grid
    particle = grid[y][x]
    if not particle or not particle.material or not particle.material.reacts_with:
        return
    reacts = particle.material.reacts_with

    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nx, ny = x + dx, y + dy
            if 0 <= nx < world.width and 0 <= ny < world.height:
                neighbor = grid[ny][nx]
                if neighbor and neighbor.type in reacts:
                    reaction_func = globals().get(reacts[neighbor.type])
                    if callable(reaction_func):
                        reaction_func(world, x, y, nx, ny)

                        if grid[y][x] is not particle or particle.vx or particle.vy:
                            return


def handle_phase_transition(world, x, y):
    p = world.grid[y][x]
    if p is None or p.material is None:
        return False

    mat = p.material
    t = p.temperature
    new_type = None
    point = None

    if mat.freezing_point is not None and t <= mat.freezing_point:
        new_type = mat.become_to[0] if len(mat.become_to) > 0 else None
        point = mat.freezing_point
    elif mat.boiling_point is not None and t >= mat.boiling_point:
        new_type = mat.become_to[1] if len(mat.become_to) > 1 else None
        point = mat.boiling_point
    elif mat.meltable and mat.melting_point is not None and t >= mat.melting_point:
        new_type = mat.become_to[0] if len(mat.become_to) > 0 else None
        point = mat.melting_point

    if new_type is None or point is None:
        if p.phase_energy:
            p.phase_energy *= _PH.phase_energy_decay
            if p.phase_energy < 0.01:
                p.phase_energy = 0.0
        return False

    if mat.condense_needs_ceiling and not _ceiling_above(world, x, y):
        return False

    latent = mat.latent_heat
    if latent > 0:
        p.phase_energy += abs(t - point) * mat.heat_capacity
        p.temperature = point
        if p.phase_energy < latent:
            _keep_awake(world, x, y)
            return False

    world.set(x, y, Particle(new_type, temperature=p.temperature))
    return True


def powder_physics(world, x, y):
    grid = world.grid
    particle = grid[y][x]
    if not particle:
        return
    W = world.width
    H = world.height

    dx, dy = get_gravity_vector(physics_rotation)

    steps = max(random.choice([1, 2]), int(particle.fall))
    if _fall_run(world, grid, W, H, x, y, dx, dy, steps, _free):
        _accelerate(particle)
        return
    particle.fall = 0.0

    side_dx = -dy
    side_dy = dx
    directions = []

    for sign in (1, -1):
        sx = side_dx * sign
        sy = side_dy * sign
        x1, y1 = x + sx + dx, y + sy + dy
        x2, y2 = x + sx * 2 + dx, y + sy * 2 + dy
        if _free(grid, W, H, x1, y1) and _diag_ok(grid, W, H, x, y, x1, y1):
            if _free(grid, W, H, x2, y2):
                directions.append((sx * 2 + dx, sy * 2 + dy))
            else:
                directions.append((sx + dx, sy + dy))

    if directions:
        ddx, ddy = random.choice(directions)
        world.move_to(x, y, x + ddx, y + ddy)


def clay_physics(world, x, y):
    grid = world.grid
    particle = grid[y][x]
    if not particle:
        return

    dx, dy = get_gravity_vector(physics_rotation)
    if _fall_run(world, grid, world.width, world.height, x, y, dx, dy, max(1, int(particle.fall)), _free):
        _accelerate(particle)
    else:
        particle.fall = 0.0


def wet_powder_physics(world, x, y):
    grid = world.grid
    particle = grid[y][x]
    if not particle:
        return
    W = world.width
    H = world.height

    _keep_awake(world, x, y)

    if particle.age > 0:
        particle.age += 1

    dx, dy = get_gravity_vector(physics_rotation)

    base = 2 if random.random() < _PH.wet_sand_fast_fall_chance else 1
    if _fall_run(world, grid, W, H, x, y, dx, dy, max(base, int(particle.fall)), _free):
        _accelerate(particle)
        return
    particle.fall = 0.0

    side_dx = -dy
    side_dy = dx
    directions = []

    for side in (-1, 1):
        sx = x + dx + side_dx * side
        sy = y + dy + side_dy * side
        if _free(grid, W, H, sx, sy) and _diag_ok(grid, W, H, x, y, sx, sy):
            directions.append((sx, sy))

    if directions:
        nx, ny = random.choice(directions)
        world.move_to(x, y, nx, ny)


def _kinetic_target_free(target):
    return target is None or bool(target.material and target.material.physics_type[0] == 2)


def kinetic_sand_physics(world, x, y):
    grid = world.grid
    particle = grid[y][x]
    if not particle:
        return
    W = world.width
    H = world.height

    neighbors = 0
    for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
        if 0 <= nx < W and 0 <= ny < H:
            neighbor = grid[ny][nx]
            if neighbor and neighbor.type == "Кинетический песок":
                neighbors += 1

    stickiness = min(_PH.kinetic_max_stickiness, neighbors / 4.0)

    dx, dy = get_gravity_vector(physics_rotation)
    side_dx = -dy
    side_dy = dx

    def free(g, w_, h_, cx, cy):
        return 0 <= cx < w_ and 0 <= cy < h_ and _kinetic_target_free(g[cy][cx])

    if random.random() < stickiness:
        for cx, cy in ((x + dx, y + dy), (x + dx * 2, y + dy * 2),
                       (x + dx + side_dx, y + dy + side_dy), (x + dx - side_dx, y + dy - side_dy)):
            if free(grid, W, H, cx, cy):
                _keep_awake(world, x, y)
                break
        return

    base = 2 if random.random() < _PH.kinetic_fast_fall_chance else 1
    if _fall_run(world, grid, W, H, x, y, dx, dy, max(base, int(particle.fall)), free):
        _accelerate(particle)
        return
    particle.fall = 0.0

    directions = []
    for side in (-1, 1):
        nx = x + side_dx * side + dx
        ny = y + side_dy * side + dy
        if free(grid, W, H, nx, ny) and _diag_ok(grid, W, H, x, y, nx, ny):
            directions.append((nx, ny))

    if directions and random.random() < _PH.kinetic_slide_chance:
        nx, ny = random.choice(directions)
        world.move_to(x, y, nx, ny)
        return

    if directions or free(grid, W, H, x + dx, y + dy):
        _keep_awake(world, x, y)


def alien_powder_physics(world, x, y):
    grid = world.grid
    particle = grid[y][x]
    if not particle:
        return
    W = world.width
    H = world.height

    dx, dy = get_gravity_vector(physics_rotation)
    dx, dy = -dx, -dy

    steps = max(random.choice([1, 2]), int(particle.fall))
    if _fall_run(world, grid, W, H, x, y, dx, dy, steps, _is_none):
        _accelerate(particle)
        return
    particle.fall = 0.0

    side_dx = -dy
    side_dy = dx
    directions = []

    for sign in (1, -1):
        sx = side_dx * sign
        sy = side_dy * sign
        x1, y1 = x + sx + dx, y + sy + dy
        x2, y2 = x + sx * 2 + dx, y + sy * 2 + dy
        if _is_none(grid, W, H, x1, y1) and _diag_ok(grid, W, H, x, y, x1, y1):
            if _is_none(grid, W, H, x2, y2):
                directions.append((sx * 2 + dx, sy * 2 + dy))
            else:
                directions.append((sx + dx, sy + dy))

    if directions:
        ddx, ddy = random.choice(directions)
        world.move_to(x, y, x + ddx, y + ddy)


_LIQUID_DOWN = (1, 0, -1)
_LIQUID_SIDE = (-1, 1, 2, -2, -3, 3)


def _hop_clear(grid, W, H, x, y, hx, hy, b):
    step = 1 if b > 0 else -1
    for i in range(1, abs(b)):
        cx = x + hx * i * step
        cy = y + hy * i * step
        if cx < 0 or cx >= W or cy < 0 or cy >= H:
            return False
        t = grid[cy][cx]
        if t is not None and (t.body is not None or t.material is None
                              or t.material.physics_type[0] in (0, 1)):
            return False
    return True


def liquid_physics(world, x, y):
    grid = world.grid
    particle = grid[y][x]
    if not particle:
        return
    W = world.width
    H = world.height

    viscosity = particle.material.viscosity
    if viscosity and random.random() < viscosity:
        _keep_awake(world, x, y)
        return

    gx, gy = get_gravity_vector(physics_rotation)
    sx, sy = -gy, gx
    hx, hy = gy, -gx

    k = random.choice(_LIQUID_DOWN)
    if k == 0:
        if _fall_run(world, grid, W, H, x, y, gx, gy, max(1, int(particle.fall)), _is_none):
            _accelerate(particle)
            return
        particle.fall = 0.0
    else:
        nx = x + gx + sx * k
        ny = y + gy + sy * k
        if 0 <= nx < W and 0 <= ny < H and grid[ny][nx] is None and _diag_ok(grid, W, H, x, y, nx, ny):
            particle.fall = 0.0
            world.move_to(x, y, nx, ny)
            return

    b = random.choice(_LIQUID_SIDE)
    nx = x + hx * b
    ny = y + hy * b
    if (0 <= nx < W and 0 <= ny < H and grid[ny][nx] is None
            and (abs(b) == 1 or _hop_clear(grid, W, H, x, y, hx, hy, b))):
        particle.fall = 0.0
        world.move_to(x, y, nx, ny)
        return

    for k in _LIQUID_DOWN:
        cx, cy = x + gx + sx * k, y + gy + sy * k
        if _is_none(grid, W, H, cx, cy) and (k == 0 or _diag_ok(grid, W, H, x, y, cx, cy)):
            _keep_awake(world, x, y)
            return
    for b in _LIQUID_SIDE:
        if (_is_none(grid, W, H, x + hx * b, y + hy * b)
                and (abs(b) == 1 or _hop_clear(grid, W, H, x, y, hx, hy, b))):
            _keep_awake(world, x, y)
            return


def solid_physics(world, x, y):
    pass


def gas_physics(world, x, y):
    grid = world.grid
    particle = grid[y][x]
    if not particle:
        return
    W = world.width
    H = world.height

    mat = particle.material
    if mat.freezing_point is not None or mat.boiling_point is not None:
        diff = _AMBIENT - particle.temperature
        if diff > _PH.gas_cooling_deadzone or diff < -_PH.gas_cooling_deadzone:
            particle.temperature += diff * _PH.gas_cooling_rate
            _keep_awake(world, x, y)

    gx, gy = get_gravity_vector(physics_rotation)
    ux, uy = -gx, -gy
    hx, hy = gy, -gx

    for d in (1, 2):
        bx = x + ux * d
        by = y + uy * d
        if bx < 0 or bx >= W or by < 0 or by >= H:
            continue

        jitter = 0
        if random.random() < _PH.gas_jitter_chance:
            jitter = random.choice([-1, 1])

        nx = bx + hx * jitter
        ny = by + hy * jitter

        if _free(grid, W, H, nx, ny):
            world.move_to(x, y, nx, ny)
            return

    for d in (1, 2):
        bx = x + ux * d
        by = y + uy * d
        if bx < 0 or bx >= W or by < 0 or by >= H:
            continue
        for jitter in (-1, 0, 1):
            if _free(grid, W, H, bx + hx * jitter, by + hy * jitter):
                _keep_awake(world, x, y)
                return


def update_fire_physics(world, x, y):
    grid = world.grid
    p = grid[y][x]
    if not p or not p.material:
        return

    W = world.width
    H = world.height

    for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
        n = _cell(grid, W, H, nx, ny)
        if n is not None and n.material is not None and n.material.extinguishes:
            world.set(x, y, None)
            return

    _keep_awake(world, x, y)

    p.age += 1
    lifespan = p.max_age
    old_color = p.color

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

    if p.color != old_color:
        world.draw_cell(x, y)

    if p.age < lifespan * _PH.fire_rise_fraction:
        gx, gy = get_gravity_vector(physics_rotation)
        ux, uy = -gx, -gy
        hx, hy = gy, -gx
        for d in (1, 2):
            bx = x + ux * d
            by = y + uy * d
            if bx < 0 or bx >= W or by < 0 or by >= H:
                continue

            jitter = 0
            if random.random() < _PH.fire_jitter_chance:
                jitter = random.choice([-1, 1])

            nx = bx + hx * jitter
            ny = by + hy * jitter
            if _is_none(grid, W, H, nx, ny):
                world.move_to(x, y, nx, ny)
                return

    if p.age >= lifespan:
        world.set(x, y, None)


