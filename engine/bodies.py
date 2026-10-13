import math
from collections import deque

from . import damage
from .physics import physics as _phys

MAX_BODY_CELLS = 2048
GRAVITY = 0.12
MAX_SPEED = 6.0
REST_TICKS = 6
SUBSTEP = 0.5
MAX_OMEGA = 0.12
MAX_OMEGA_GRAB = 0.3
TIP_ACCEL = 0.012
SUPPORT_TOLERANCE = 0.25
JAM_TICKS = 12
IMPACT_MIN_SPEED = 0.45
GRAB_STIFFNESS = 0.3
GRAB_MAX_SPEED = 6.0
GRAB_STRENGTH = 0.6

_RELOCATE_OFFSETS = sorted(
    ((dx, dy) for dx in range(-4, 5) for dy in range(-4, 5) if dx or dy),
    key=lambda d: d[0] * d[0] + d[1] * d[1],
)


def _density(p):
    return p.material.density if p.material is not None else 1.0


class Body:
    def __init__(self, world, cells, com, px, py, theta=0.0):
        self.world = world
        self.cells = cells
        self.com = com
        self.px = px
        self.py = py
        self.theta = theta
        self.vx = 0.0
        self.vy = 0.0
        self.omega = 0.0
        self.cover = {}
        self.rest_ticks = 0
        self.resting = False
        self.bbox = (0, 0, 0, 0)
        self.grab = None
        self.grab_local = None
        self.dead = False
        self.jam = 0
        self.mass = 1.0
        self.inertia = 1.0
        self.radius = 1.0
        for p in cells.values():
            p.body = self
        self._update_shape()

    def _update_shape(self):
        comx, comy = self.com
        mass = 0.0
        inertia = 0.0
        far = 0.0
        for (i, j), p in self.cells.items():
            d = _density(p)
            rx = i + 0.5 - comx
            ry = j + 0.5 - comy
            r2 = rx * rx + ry * ry
            mass += d
            inertia += d * (r2 + 1.0 / 6.0)
            if r2 > far:
                far = r2
        self.mass = max(mass, 1e-6)
        self.inertia = max(inertia, 1e-6)
        self.radius = 1.0 + math.sqrt(far)

    def _pose_cover(self, px, py, th):
        comx, comy = self.com
        cells = self.cells
        if th == 0.0:
            kx = math.floor(px - comx + 0.5)
            ky = math.floor(py - comy + 0.5)
            return {(i + kx, j + ky): (i, j) for (i, j) in cells}

        c = math.cos(th)
        s = math.sin(th)
        r = self.radius
        x_lo = int(math.floor(px - r))
        x_hi = int(math.floor(px + r)) + 1
        y_lo = int(math.floor(py - r))
        y_hi = int(math.floor(py + r)) + 1
        floor = math.floor
        cover = {}
        for Y in range(y_lo, y_hi + 1):
            wy = Y + 0.5 - py
            for X in range(x_lo, x_hi + 1):
                wx = X + 0.5 - px
                key = (floor(comx + wx * c + wy * s), floor(comy - wx * s + wy * c))
                if key in cells:
                    cover[(X, Y)] = key

        centers = {}
        for key in cells:
            rx = key[0] + 0.5 - comx
            ry = key[1] + 0.5 - comy
            wx = px + rx * c - ry * s
            wy = py + rx * s + ry * c
            centers[key] = (wx, wy)
            fc = (floor(wx), floor(wy))
            if fc not in cover:
                cover[fc] = key

        present = set(cover.values())
        if len(present) != len(cells):
            for key, (wx, wy) in centers.items():
                if key in present:
                    continue
                bx = floor(wx)
                by = floor(wy)
                best = None
                best_d = 1e9
                for ddx in (-1, 0, 1):
                    for ddy in (-1, 0, 1):
                        cell = (bx + ddx, by + ddy)
                        if cell in cover:
                            continue
                        d = (cell[0] + 0.5 - wx) ** 2 + (cell[1] + 0.5 - wy) ** 2
                        if d < best_d:
                            best, best_d = cell, d
                if best is not None:
                    cover[best] = key
        return cover

    def _collides(self, cover):
        grid = self.world.grid
        W = self.world.width
        H = self.world.height
        for (X, Y) in cover:
            if X < 0 or X >= W or Y < 0 or Y >= H:
                return True
            t = grid[Y][X]
            if t is None or t.body is self:
                continue
            m = t.material
            if t.body is None and m is not None and m.physics_type[0] in (2, 3, 4):
                continue
            return True
        return False

    def _try_pose(self, px, py, th):
        cover = self._pose_cover(px, py, th)
        if self._collides(cover):
            return None
        return cover

    def _apply_cover(self, new_cover):
        world = self.world
        grid = world.grid
        old = self.cover

        for cell in old:
            if cell not in new_cover:
                X, Y = cell
                t = grid[Y][X]
                if t is not None and t.body is self:
                    world.set(X, Y, None)

        displaced = []
        cells = self.cells
        for cell, key in new_cover.items():
            X, Y = cell
            p = cells[key]
            cur = grid[Y][X]
            if cur is p:
                continue
            if cur is not None and cur.body is not self:
                displaced.append((X, Y, cur))
            world.set(X, Y, p)
        self.cover = new_cover

        if displaced:
            vacated = [c for c in old if c not in new_cover and grid[c[1]][c[0]] is None]
            for X, Y, particle in displaced:
                if vacated:
                    j = min(range(len(vacated)),
                            key=lambda k: (vacated[k][0] - X) ** 2 + (vacated[k][1] - Y) ** 2)
                    nx, ny = vacated.pop(j)
                    world.set(nx, ny, particle)
                else:
                    self._relocate(X, Y, particle)

    def _relocate(self, X, Y, particle):
        world = self.world
        grid = world.grid
        W = world.width
        H = world.height
        for dx, dy in _RELOCATE_OFFSETS:
            nx, ny = X + dx, Y + dy
            if 0 <= nx < W and 0 <= ny < H and grid[ny][nx] is None and (nx, ny) not in self.cover:
                world.set(nx, ny, particle)
                return

    def remove_particle(self, particle):
        key = None
        for k, v in self.cells.items():
            if v is particle:
                key = k
                break
        if key is None:
            return
        del self.cells[key]
        particle.body = None
        particle.baked = None
        self.cover = {c: k for c, k in self.cover.items() if k != key}
        self._after_cells_changed()

    def _reconcile(self):
        grid = self.world.grid
        cells = self.cells
        lost = set()
        for (X, Y), key in self.cover.items():
            p = cells.get(key)
            if p is not None and grid[Y][X] is not p:
                lost.add(key)
        if not lost:
            return

        for (X, Y), key in self.cover.items():
            if key in lost and grid[Y][X] is cells[key]:
                self.world.set(X, Y, None)
        for key in lost:
            p = cells.pop(key)
            p.body = None
            p.baked = None
        self.cover = {c: k for c, k in self.cover.items() if k not in lost}
        self._after_cells_changed()

    def _components(self):
        keys = set(self.cells)
        comps = []
        while keys:
            start = keys.pop()
            comp = {start}
            queue = deque([start])
            while queue:
                i, j = queue.popleft()
                for nb in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                    if nb in keys:
                        keys.remove(nb)
                        comp.add(nb)
                        queue.append(nb)
            comps.append(comp)
        comps.sort(key=len, reverse=True)
        return comps

    def _com_of(self, keys):
        total = 0.0
        sx = 0.0
        sy = 0.0
        for key in keys:
            d = _density(self.cells[key])
            total += d
            sx += d * (key[0] + 0.5)
            sy += d * (key[1] + 0.5)
        return (sx / total, sy / total)

    def _world_offset(self, new_com):
        c = math.cos(self.theta)
        s = math.sin(self.theta)
        dx = new_com[0] - self.com[0]
        dy = new_com[1] - self.com[1]
        return self.px + dx * c - dy * s, self.py + dx * s + dy * c

    def _after_cells_changed(self):
        if not self.cells:
            self._die()
            return
        comps = self._components()

        for comp in comps[1:]:
            new_com = self._com_of(comp)
            npx, npy = self._world_offset(new_com)
            piece = {k: self.cells.pop(k) for k in comp}
            body = Body(self.world, piece, new_com, npx, npy, self.theta)
            body.cover = {c: k for c, k in self.cover.items() if k in comp}
            body.vx = self.vx - self.omega * (npy - self.py)
            body.vy = self.vy + self.omega * (npx - self.px)
            body.omega = self.omega
            self.world.bodies.append(body)
            self.cover = {c: k for c, k in self.cover.items() if k not in comp}

        new_com = self._com_of(self.cells)
        npx, npy = self._world_offset(new_com)
        self.vx -= self.omega * (npy - self.py)
        self.vy += self.omega * (npx - self.px)
        self.com = new_com
        self.px, self.py = npx, npy
        self._update_shape()
        self.resting = False
        self.rest_ticks = 0
        if self.grab is not None:
            self.grab_local = None

    def _die(self):
        self.dead = True
        if self in self.world.bodies:
            self.world.bodies.remove(self)

    def dissolve(self):
        for p in self.cells.values():
            p.body = None
            p.baked = None
        self.cells = {}
        self._die()

    def apply_impulse(self, fx, fy, wx, wy):
        self.vx += fx / self.mass
        self.vy += fy / self.mass
        self.omega += ((wx - self.px) * fy - (wy - self.py) * fx) / self.inertia
        self.resting = False
        self.rest_ticks = 0

    def begin_grab(self, fx, fy):
        rx = fx - self.px
        ry = fy - self.py
        c = math.cos(self.theta)
        s = math.sin(self.theta)
        self.grab_local = (rx * c + ry * s, -rx * s + ry * c)
        self.grab = (fx, fy)
        self.resting = False
        self.rest_ticks = 0

    def end_grab(self):
        self.grab = None
        self.grab_local = None

    def update(self):
        world = self.world
        if self.resting:
            x0, y0, x1, y1 = self.bbox
            if self.grab is None and not world.region_awake(x0, y0, x1, y1):
                return
            self.resting = False
            self.rest_ticks = 0

        self._reconcile()
        if self.dead or not self.cells:
            return
        self._dynamics()

    def _gravity(self):
        return _phys.get_gravity_vector(_phys.physics_rotation)

    def _contacts(self, cover, gdx, gdy):
        grid = self.world.grid
        W = self.world.width
        H = self.world.height
        out = []
        for (X, Y) in cover:
            nx, ny = X + gdx, Y + gdy
            if nx < 0 or nx >= W or ny < 0 or ny >= H:
                out.append((X, Y))
                continue
            t = grid[ny][nx]
            if t is None or t.body is self:
                continue
            m = t.material
            if t.body is None and m is not None and m.physics_type[0] in (2, 3, 4):
                continue
            out.append((X, Y))
        return out

    def _rotate_about(self, pivot_x, pivot_y, dth):
        c = math.cos(dth)
        s = math.sin(dth)
        rx = self.px - pivot_x
        ry = self.py - pivot_y
        npx = pivot_x + rx * c - ry * s
        npy = pivot_y + rx * s + ry * c
        nth = self.theta + dth
        cover = self._try_pose(npx, npy, nth)
        if cover is None:
            return None
        self.px, self.py, self.theta = npx, npy, nth
        return cover

    def _buoyancy(self, gdx, gdy):
        grid = self.world.grid
        W = self.world.width
        H = self.world.height
        columns = {}
        for (X, Y) in self.cover:
            u = X * gdy - Y * gdx
            h = -(X * gdx + Y * gdy)
            columns.setdefault(u, []).append((h, X, Y))

        fx = 0.0
        fy = 0.0
        tau = 0.0
        count = 0
        for cells in columns.values():
            cells.sort(reverse=True)
            submerged = False
            density = 0.0
            prev_h = None
            for h, X, Y in cells:
                if prev_h is None or prev_h - h != 1:
                    submerged = False
                for nx, ny in ((X + 1, Y), (X - 1, Y), (X, Y + 1), (X, Y - 1)):
                    if 0 <= nx < W and 0 <= ny < H:
                        t = grid[ny][nx]
                        if (t is not None and t.body is None and t.material is not None
                                and t.material.physics_type[0] == 2):
                            submerged = True
                            density = t.material.density
                            break
                if submerged:
                    count += 1
                    f = GRAVITY * density
                    fx -= gdx * f
                    fy -= gdy * f
                    rx = X + 0.5 - self.px
                    ry = Y + 0.5 - self.py
                    tau += rx * (-gdy * f) - ry * (-gdx * f)
                prev_h = h

        if count == 0:
            return 0.0
        self.vx += fx / self.mass
        self.vy += fy / self.mass
        self.omega += tau / self.inertia
        return count / max(1, len(self.cover))

    def _grab_impulse(self):
        tx, ty = self.grab
        lx, ly = self.grab_local if self.grab_local is not None else (0.0, 0.0)
        c = math.cos(self.theta)
        s = math.sin(self.theta)
        rx = lx * c - ly * s
        ry = lx * s + ly * c
        dx = tx - (self.px + rx)
        dy = ty - (self.py + ry)
        vdx = max(-GRAB_MAX_SPEED, min(GRAB_MAX_SPEED, dx * GRAB_STIFFNESS))
        vdy = max(-GRAB_MAX_SPEED, min(GRAB_MAX_SPEED, dy * GRAB_STIFFNESS))
        ex = vdx - (self.vx - self.omega * ry)
        ey = vdy - (self.vy + self.omega * rx)
        im = 1.0 / self.mass
        ii = 1.0 / self.inertia
        k11 = im + ry * ry * ii
        k12 = -rx * ry * ii
        k22 = im + rx * rx * ii
        det = k11 * k22 - k12 * k12
        if det < 1e-12:
            return
        jx = (k22 * ex - k12 * ey) / det * GRAB_STRENGTH
        jy = (-k12 * ex + k11 * ey) / det * GRAB_STRENGTH
        self.vx += jx * im
        self.vy += jy * im
        self.omega += (rx * jy - ry * jx) * ii

    def _dynamics(self):
        gdx, gdy = self._gravity()
        start_pose = (self.px, self.py, self.theta)
        cover = self.cover
        grabbed = self.grab is not None

        self.vx += gdx * GRAVITY
        self.vy += gdy * GRAVITY
        frac = self._buoyancy(gdx, gdy)
        if frac > 0.0:
            drag = 1.0 - 0.12 * frac
            self.vx *= drag
            self.vy *= drag
            self.omega *= 1.0 - 0.2 * frac
        if grabbed:
            self._grab_impulse()
            limit = MAX_OMEGA_GRAB
        else:
            limit = MAX_OMEGA
        self.omega = max(-limit, min(limit, self.omega))

        speed = math.hypot(self.vx, self.vy)
        if speed > MAX_SPEED:
            self.vx *= MAX_SPEED / speed
            self.vy *= MAX_SPEED / speed

        impact_speed = 0.0
        blocked = []
        steps = max(1, int(math.ceil(max(abs(self.vx), abs(self.vy)) / SUBSTEP)))
        dx = self.vx / steps
        dy = self.vy / steps
        for _ in range(steps):
            c = self._try_pose(self.px + dx, self.py + dy, self.theta)
            if c is not None:
                self.px += dx
                self.py += dy
                cover = c
                continue
            ok_x = ok_y = False
            if dx:
                c = self._try_pose(self.px + dx, self.py, self.theta)
                if c is not None:
                    self.px += dx
                    cover = c
                    ok_x = True
            if dy:
                c = self._try_pose(self.px, self.py + dy, self.theta)
                if c is not None:
                    self.py += dy
                    cover = c
                    ok_y = True
            if dx and not ok_x:
                impact_speed = max(impact_speed, abs(self.vx))
                blocked.append((1 if self.vx > 0 else -1, 0))
                self.vx = 0.0
                dx = 0.0
            if dy and not ok_y:
                impact_speed = max(impact_speed, abs(self.vy))
                blocked.append((0, 1 if self.vy > 0 else -1))
                self.vy = 0.0
                dy = 0.0
            if not ok_x and not ok_y:
                break

        contacts = self._contacts(cover, gdx, gdy)
        stable = False
        rotated_done = False
        if contacts and not grabbed:
            rotated_done = True
            self.vx *= 0.6
            self.vy *= 0.6
            if abs(self.vx) < 0.03:
                self.vx = 0.0
            if abs(self.vy) < 0.03:
                self.vy = 0.0

            def u_of(X, Y):
                return gdy * (X + 0.5) - gdx * (Y + 0.5)

            us = [u_of(X, Y) for (X, Y) in contacts]
            u_lo = min(us) - 0.5 - SUPPORT_TOLERANCE
            u_hi = max(us) + 0.5 + SUPPORT_TOLERANCE
            u_c = gdy * self.px - gdx * self.py
            if u_lo <= u_c <= u_hi:
                stable = True
                self.omega = 0.0
            else:
                if u_c > u_hi:
                    X, Y = max(contacts, key=lambda c_: u_of(*c_))
                else:
                    X, Y = min(contacts, key=lambda c_: u_of(*c_))
                side = 1.0 if u_c > u_hi else -1.0
                pivot_x = X + 0.5 + 0.5 * gdx + 0.5 * side * gdy
                pivot_y = Y + 0.5 + 0.5 * gdy - 0.5 * side * gdx
                rx = self.px - pivot_x
                ry = self.py - pivot_y
                sign = 1.0 if (rx * gdy - ry * gdx) > 0 else -1.0
                self.omega = max(-MAX_OMEGA, min(MAX_OMEGA, self.omega + sign * TIP_ACCEL))
                if abs(self.omega) < 0.02:
                    self.omega = sign * 0.02
                rotated = None
                for scale in (1.0, 0.5, 0.25):
                    rotated = self._rotate_about(pivot_x, pivot_y, self.omega * scale)
                    if rotated is not None:
                        break
                if rotated is not None:
                    cover = rotated
                    self.jam = 0
                else:
                    self.omega = 0.0
                    self.jam += 1
                    direction = 1.0 if u_c > u_hi else -1.0
                    self.vx += direction * gdy * 0.35
                    self.vy += direction * -gdx * 0.35

        if not rotated_done and self.omega:
            self.omega *= 0.97 if grabbed else 0.995
            rotated = None
            for scale in (1.0, 0.5):
                rotated = self._rotate_about(self.px, self.py, self.omega * scale)
                if rotated is not None:
                    break
            if rotated is not None:
                cover = rotated
            else:
                self.omega = 0.0

        if cover != self.cover:
            self._apply_cover(cover)
        moved = (self.px, self.py, self.theta) != start_pose
        if moved:
            self.jam = 0
        elif blocked and not grabbed:
            self.jam += 1
            if self.jam >= JAM_TICKS:
                stable = True
                self.vx = 0.0
                self.vy = 0.0
                self.omega = 0.0

        if impact_speed > IMPACT_MIN_SPEED and blocked:
            self._impact(blocked, impact_speed)

        if stable and not moved and abs(self.vx) < 0.05 and abs(self.vy) < 0.05 and not grabbed:
            self.rest_ticks += 1
            if self.rest_ticks >= REST_TICKS:
                xs = [X for X, _ in self.cover]
                ys = [Y for _, Y in self.cover]
                self.bbox = (min(xs), min(ys), max(xs), max(ys))
                self.resting = True
        else:
            self.rest_ticks = 0

    def _impact(self, axes, speed):
        world = self.world
        grid = world.grid
        W = world.width
        H = world.height
        pairs = []
        for (X, Y) in self.cover:
            for sx, sy in axes:
                nx, ny = X + sx, Y + sy
                if 0 <= nx < W and 0 <= ny < H:
                    t = grid[ny][nx]
                    if t is None or t.body is self:
                        continue
                    m = t.material
                    if t.body is None and m is not None and m.physics_type[0] in (2, 3, 4):
                        continue
                    pairs.append((X, Y, nx, ny))
        if not pairs:
            return
        gdx, gdy = self._gravity()
        damage.apply_impact(world, pairs, 0.5 * self.mass * speed * speed, (-gdx, -gdy))


def is_selectable(world, x, y):
    if not world.in_bounds(x, y) or world.is_border(x, y):
        return False
    p = world.grid[y][x]
    return (
        p is not None and p.body is None and p.material is not None
        and p.material.physics_type[0] == 0 and not (p.vx or p.vy)
    )


def _components(coords):
    coords = set(coords)
    comps = []
    while coords:
        start = coords.pop()
        comp = {start}
        queue = deque([start])
        while queue:
            x, y = queue.popleft()
            for nb in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if nb in coords:
                    coords.remove(nb)
                    comp.add(nb)
                    queue.append(nb)
        comps.append(comp)
    return comps


def make_body(world, coords):
    min_x = min(x for x, _ in coords)
    min_y = min(y for _, y in coords)
    cells = {}
    cover = {}
    total = 0.0
    sx = 0.0
    sy = 0.0
    for (x, y) in coords:
        key = (x - min_x, y - min_y)
        p = world.grid[y][x]
        p.baked = world.cell_rgba(x, y)
        cells[key] = p
        cover[(x, y)] = key
        d = _density(p)
        total += d
        sx += d * (key[0] + 0.5)
        sy += d * (key[1] + 0.5)
    com = (sx / total, sy / total)
    body = Body(world, cells, com, com[0] + min_x, com[1] + min_y)
    body.cover = cover
    world.bodies.append(body)
    return body


def make_bodies(world, coords):
    valid = {(x, y) for (x, y) in coords if is_selectable(world, x, y)}
    bodies = []
    skipped = 0
    for comp in _components(valid):
        if len(comp) > MAX_BODY_CELLS:
            skipped += 1
            continue
        bodies.append(make_body(world, comp))
    return bodies, skipped


def select_rect(world, x0, y0, x1, y1):
    xa, xb = sorted((x0, x1))
    ya, yb = sorted((y0, y1))
    return [(x, y) for y in range(ya, yb + 1) for x in range(xa, xb + 1)]


def select_flood(world, x, y):
    if not is_selectable(world, x, y):
        return []
    seen = {(x, y)}
    queue = deque([(x, y)])
    while queue:
        cx, cy = queue.popleft()
        for nb in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if nb not in seen and is_selectable(world, *nb):
                seen.add(nb)
                queue.append(nb)
                if len(seen) > MAX_BODY_CELLS * 4:
                    return list(seen)
    return list(seen)


def body_at(world, x, y):
    best = None
    best_d = 99
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            nx, ny = x + dx, y + dy
            if world.in_bounds(nx, ny):
                p = world.grid[ny][nx]
                if p is not None and p.body is not None:
                    d = abs(dx) + abs(dy)
                    if d < best_d:
                        best, best_d = p.body, d
    return best


def grab_at(world, fx, fy):
    body = body_at(world, int(fx), int(fy))
    if body is not None:
        body.begin_grab(fx, fy)
    return body


def update_bodies(world):
    for body in list(world.bodies):
        if not body.dead:
            body.update()
    world.bodies[:] = [b for b in world.bodies if not b.dead]


_BLOB_SHAPE = ("  ####  ", " ###### ", "########", "####### ", " ###### ", "   ###  ")


def spawn_blob(world, gx, gy, material="Скала"):
    from .particle import Particle
    coords = []
    h = len(_BLOB_SHAPE)
    w_ = len(_BLOB_SHAPE[0])
    for j, row in enumerate(_BLOB_SHAPE):
        for i, ch in enumerate(row):
            if ch != "#":
                continue
            x, y = gx - w_ // 2 + i, gy - h // 2 + j
            if world.in_bounds(x, y) and not world.is_border(x, y) and world.grid[y][x] is None:
                world.set(x, y, Particle(material))
                coords.append((x, y))
    return make_bodies(world, coords)[0]
