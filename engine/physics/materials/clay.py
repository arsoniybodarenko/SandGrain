from engine.physics.physics import get_gravity_vector, physics_rotation


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