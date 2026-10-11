import random
from .materials import MATERIALS


class Particle:
    def __init__(self, type_name, color=None, temperature=None):
        self.type = type_name
        self.material = MATERIALS.get(type_name)
        if self.material is None:
            raise ValueError(f"Неизвестный материал: {type_name!r}")

        self.updated = -1  # номер тика физики, в котором частица уже обработана
        self.flooded = 0

        # 0 это допустимая температура (раньше `if temperature:` терял её)
        if temperature is not None:
            self.temperature = temperature
        elif self.material.temperature is not None:
            self.temperature = self.material.temperature
        else:
            self.temperature = 20.0

        self.burning = False
        self.age = 0
        if self.material.name in ("Огонь", "Гиперогонь"):
            self.max_age = 25 + random.randint(-10, 10)
        else:
            self.max_age = None

        # Полёт: скорость в клетках за тик и дробный остаток позиции (см. ballistic_step).
        self.vx = 0.0
        self.vy = 0.0
        self.fx = 0.0
        self.fy = 0.0

        # Твёрдое тело (engine/bodies.py), в состав которого входит частица, либо None.
        self.body = None

        self.color = tuple(color) if color else tuple(self.material.color)
        self.opacity = self.material.opacity
