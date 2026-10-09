import pygame
import random
import re
from .constants import *

frame_same_cache = {}
global_fixed_cache = {}
tile_cache = {}


def adjust_color(color, amount):
    return tuple(
        max(0, min(255, c + amount))
        for c in color
    )


def apply_tint(pixels, tint_color):
    tinted = []
    for row in pixels:
        tinted_row = []
        for px in row:
            r = px[0] * tint_color[0] // 255
            g = px[1] * tint_color[1] // 255
            b = px[2] * tint_color[2] // 255
            tinted_row.append((r, g, b))
        tinted.append(tinted_row)
    return tinted


def parse_random_args(expr):
    start = expr.find("random(")
    if start == -1:
        return []
    inner = expr[start + 7: expr.find(")", start)]
    return [int(a.strip()) for a in inner.split(",")]


def stable_hash(x, y, char):
    return (x * 73856093) ^ (y * 19349663) ^ (ord(char) * 83492791)


def evaluate_texture_color(char, palette, base_color, x, y, width, height, additional_colors=None, tile_key=None):
    if additional_colors is None:
        additional_colors = {}

    expr = palette.get(char)
    if not expr:
        return base_color

    def clamp(c):
        return max(0, min(255, c))

    def apply(amount):
        if isinstance(amount, tuple):
            return amount
        return tuple(clamp(c + amount) for c in base_color)

    rng = random.Random(stable_hash(x, y, char))

    def split_args(s):
        args = []
        depth = 0
        current = ''
        for c in s:
            if c == ',' and depth == 0:
                args.append(current)
                current = ''
            else:
                if c == '(':
                    depth += 1
                elif c == ')':
                    depth -= 1
                current += c
        if current:
            args.append(current)
        return args

    def eval_expr(expr, context_key=None):
        expr = expr.strip()

        if expr in palette and expr != char and not re.search(r"[()\d]", expr):
            return eval_expr(palette[expr], context_key)

        if expr.startswith("additional("):
            inner = expr[11:-1].strip()
            try:
                r, g, b = map(int, inner.split(","))
                return (r, g, b)
            except:
                return additional_colors.get(inner, base_color)

        if expr.startswith("+("):
            inner = expr[2:-1].strip()
            parts = split_args(inner)

            if len(parts) != 3:
                return base_color

            r = eval_expr(parts[0].strip(), context_key)
            g = eval_expr(parts[1].strip(), context_key)
            b = eval_expr(parts[2].strip(), context_key)

            def to_int(v):
                if isinstance(v, tuple):
                    return v[0]
                return int(v)

            return (to_int(r), to_int(g), to_int(b))

        if expr.startswith("((") and expr.endswith("))"):
            inner = expr[2:-2].strip()
            parts = split_args(inner)

            if len(parts) != 3:
                return base_color

            r = eval_expr(parts[0].strip(), context_key)
            g = eval_expr(parts[1].strip(), context_key)
            b = eval_expr(parts[2].strip(), context_key)

            def to_int(v):
                if isinstance(v, tuple):
                    return v[0]
                return int(v)

            dr = to_int(r)
            dg = to_int(g)
            db = to_int(b)

            return (
                max(0, min(255, base_color[0] + dr)),
                max(0, min(255, base_color[1] + dg)),
                max(0, min(255, base_color[2] + db)),
            )

        match = re.fullmatch(r"([a-zA-Z]+)\s*([-+])\s*(\d+)", expr)
        if match:
            name = match.group(1)
            sign = match.group(2)
            number = int(match.group(3))
            offset = number if sign == "+" else -number
            base = eval_expr(name, context_key)
            if isinstance(base, tuple):
                return tuple(clamp(c + offset) for c in base)
            else:
                return apply(base + offset)

        if expr.startswith("fixed("):
            inner = expr[6:-1].strip()
            value = eval_expr(inner, context_key)
            return apply(value)

        if expr.startswith("random("):
            inner = expr[7:-1]
            parts = split_args(inner)
            values = [eval_expr(part.strip(), context_key) for part in parts]
            return apply(rng.choice(values))

        if expr.startswith("randint("):
            a, b = map(int, expr[8:-1].split(","))
            return apply(rng.randint(min(a, b), max(a, b)))

        if expr.startswith("same("):
            inner = expr[5:-1].strip()
            cache_key = (context_key if context_key else "global", char)
            if cache_key not in frame_same_cache:
                value = eval_expr(inner, context_key)
                frame_same_cache[cache_key] = value
            return apply(frame_same_cache[cache_key])

        if expr.startswith("for_tile("):
            inner = expr[9:-1].strip()
            tile_x = x // width if width > 0 else 0
            tile_y = y // height if height > 0 else 0
            tile_context = (tile_x, tile_y)
            if tile_context not in tile_cache:
                tile_cache[tile_context] = {}
            if char not in tile_cache[tile_context]:
                tile_cache[tile_context][char] = eval_expr(inner, context_key=tile_context)
            return tile_cache[tile_context][char]

        try:
            return int(expr)
        except:
            return base_color

    result = eval_expr(expr)
    return result if isinstance(result, tuple) else apply(result)


def evaluate_texture(texture_data, base_color=(255, 255, 255), tint_color=None):
    frame_same_cache.clear()
    tile_cache.clear()

    texture_lines, palette = texture_data
    height = len(texture_lines)
    width = max(len(line) for line in texture_lines) if texture_lines else 0

    additional_colors = {}
    for key, expr in palette.items():
        if expr.startswith("additional("):
            inner = expr[11:-1].strip()
            r, g, b = map(int, inner.split(","))
            additional_colors[key] = (r, g, b)

        elif expr.startswith("+("):
            additional_colors[key] = expr

    pixels = []
    for y in range(10):
        row = []
        for x in range(10):
            tile_x = x // width if width > 0 else 0
            tile_y = y // height if height > 0 else 0
            tile_key = (tile_x, tile_y)
            char_y = y % height if height > 0 else 0
            char_x = x % width if width > 0 else 0
            line = texture_lines[char_y] if char_y < len(texture_lines) else ""
            char = line[char_x] if char_x < len(line) else " "
            color = evaluate_texture_color(char, palette, base_color, x, y, width, height, additional_colors, tile_key)
            row.append(color)
        pixels.append(row)

    if tint_color:
        pixels = apply_tint(pixels, tint_color)
    return pixels


def temperature_to_color(temp):
    temp = max(-200, min(temp, 3000))

    if temp < 0:
        if temp >= -100:
            t = abs(temp) / 100
            r = 0
            g = 0
            b = int(255 * t)
        else:
            t = (abs(temp) - 100) / 100
            r = int(255 * t)
            g = int(255 * t)
            b = 255
        return (r, g, b)

    if temp < 300:
        r = int(255 * (temp / 300))
        return (r, 0, 0)

    elif temp < 600:
        g = int(128 * ((temp - 300) / 300))
        return (255, g, 0)

    elif temp < 900:
        g = 128 + int(127 * ((temp - 600) / 300))
        return (255, g, 0)

    else:
        b = int(255 * ((temp - 900) / 2100))
        return (255, 255, b)


def draw_world(screen, world, temperature_mode=False):
    arr = pygame.surfarray.pixels3d(world.surface)
    arr_alpha = pygame.surfarray.pixels_alpha(world.surface)

    for y in range(world.height):
        for x in range(world.width):
            p = world.get(x, y)
            if world.is_border(x, y):
                continue
            if not p:
                continue

            if temperature_mode and p.temperature is not None:
                color = temperature_to_color(p.temperature)
                opacity = 255
            else:
                if p.material and p.material.paintable:
                    from .draw import apply_tint
                    base_rgba = p.material.texture_map.get((x, y),
                                                           (*p.material.color, 255)) if p.material.texture_map else (
                        *p.material.color, 255)
                    base_rgb = base_rgba[:3]
                    tinted_rgb = apply_tint([[base_rgb]], p.color)[0][0]
                    color = tinted_rgb
                    opacity = int(p.material.opacity * 255) if p.material else 255
                elif p.material and p.material.texture_map and (x, y) in p.material.texture_map:
                    r, g, b, a = p.material.texture_map[(x, y)]
                    color = (r, g, b)
                    opacity = a
                else:
                    color = p.color
                    opacity = 255

            px = x * PIXEL_SIZE
            py = y * PIXEL_SIZE
            arr[px:px + PIXEL_SIZE, py:py + PIXEL_SIZE] = color
            arr_alpha[px:px + PIXEL_SIZE, py:py + PIXEL_SIZE] = opacity

    del arr
    del arr_alpha
    screen.blit(world.surface, (0, 0))
