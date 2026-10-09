import random, time
from .materials import MATERIALS

class Particle:
    def __init__(self, type_name, color=None, temperature=None):
        self.type = type_name
        self.updated = False
        self.flooded = 0
        self.material = MATERIALS.get(type_name)

        if temperature:
            self.temperature = temperature
        elif self.material and self.material.temperature:
            self.temperature = self.material.temperature
        else:
            self.temperature = 20.0

        self.burning = False
        self.age = 0
        if self.material.name in ("Огонь", "Гиперогонь"):
            self.max_age = 25 + random.randint(-10, 10)
        else:
            self.max_age = None

        if color:
            self.color = color
        elif self.material:
            self.color = tuple(self.material.color)
        else:
            self.color = (
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255)
            )

        if self.material:
            self.opacity = self.material.opacity
        else:
            self.opacity = 255