import random
from .materials import MATERIALS


class Particle:
    def __init__(self, type_name, color=None, temperature=None):
        self.type = type_name
        self.material = MATERIALS.get(type_name)
        if self.material is None:
            raise ValueError(f"Неизвестный материал: {type_name!r}")

        self.updated = -1
        self.flooded = 0

        if temperature is not None:
            self.temperature = temperature
        elif self.material.temperature is not None:
            self.temperature = self.material.temperature
        else:
            self.temperature = 20.0

        self.burning = False
        self.age = 0
        if self.material.name in ("Огонь", "Гиперогонь"):
            self.max_age = 10 + random.randint(-5, 5)
        else:
            self.max_age = None

        self.vx = 0.0
        self.vy = 0.0
        self.fx = 0.0
        self.fy = 0.0

        self.body = None
        self.baked = None

        self.color = tuple(color) if color else tuple(self.material.color)
        self.opacity = self.material.opacity