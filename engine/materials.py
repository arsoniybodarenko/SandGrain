import os

all_materials = []


class Material:
    __slots__ = (
        "name", "color", "physics_type",
        "flammable", "acid_resistant", "conduct_heat", "heat_capacity",
        "conduct_electricity", "explosive", "meltable", "freezable",
        "freezing_point", "melting_point", "boiling_point", "ignition_point",
        "temperature", "texture", "opacity", "glow", "category",
        "reacts_with", "texture_map", "become_to", "paintable", "burn"
    )

    def __init__(
            self,
            name,
            color,
            physics_type=("Твёрдое", 0),
            flammable=False,
            acid_resistant=True,
            conduct_heat=0.0,
            heat_capacity=1.0,
            conduct_electricity=0.0,
            explosive=False,
            meltable=False,
            freezable=False,
            melting_point=None,
            boiling_point=None,
            ignition_point=None,
            texture=None,
            opacity=1.0,
            glow=False,
            category=("Строительство", "Песок", 10),
            reacts_with=None,
            freezing_point=None,
            temperature=20,
            become_to=None,
            paintable=False,
            burn=None
    ):
        self.name = name
        self.color = color
        self.physics_type = physics_type
        self.flammable = flammable
        self.acid_resistant = acid_resistant
        self.conduct_heat = conduct_heat
        self.heat_capacity = heat_capacity
        self.conduct_electricity = conduct_electricity
        self.explosive = explosive
        self.meltable = meltable
        self.freezable = freezable
        self.freezing_point = freezing_point
        self.melting_point = melting_point
        self.boiling_point = boiling_point
        self.ignition_point = ignition_point
        self.temperature = temperature
        self.texture = texture
        self.opacity = opacity
        self.glow = glow
        self.category = category
        self.reacts_with = reacts_with or {}
        self.texture_map = {}
        self.become_to = become_to or ()
        self.paintable = paintable
        self.burn = burn or ()
        global all_materials
        all_materials.append(self)


def get_selected_material(selected_base, selected_variant):
    if selected_variant and selected_variant in MATERIALS:
        return selected_variant
    elif selected_base and selected_base in MATERIALS:
        return selected_base
    return None


def load_texture(name):
    path = f"assets/textures/{name}.texture"
    if not os.path.exists(path):
        return [], {}

    with open(path, "r", encoding="utf-8") as f:
        lines = [line.rstrip() for line in f if line.strip()]

    texture_lines = []
    palette = {}
    for line in lines:
        if "=" in line:
            key, expr = line.split("=", 1)
            palette[key.strip()] = expr.strip()
        else:
            texture_lines.append(line)

    return texture_lines, palette


def load_icon(name):
    path = os.path.join(os.path.dirname(__file__), "..", "assets/icons", f"{name}.icon")
    path = os.path.normpath(path)

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        return None

    grid = lines[:10]
    color_map = {}

    for line in lines[10:]:
        if "=" in line:
            key, value = line.split("=")
            key = key.strip()
            rgb = tuple(map(int, value.strip("()").split(",")))
            color_map[key] = rgb

    pixels = []
    for y in range(10):
        row = []
        for x in range(10):
            char = grid[y][x]
            color = color_map.get(char, (255, 255, 255))
            row.append(color)
        pixels.append(row)

    return pixels


MATERIALS = {
    "Песок": Material(
        name="Песок",
        color=(194, 178, 128),
        physics_type=(1, 0),
        category=("Строительство", "Песок", 0),
        conduct_heat=0.1,
        opacity=1.0,
        texture=load_texture("Песок")
    ),
    "Глина": Material(
        name="Глина",
        color=(125, 85, 65),
        physics_type=(1, 4),
        category=("Строительство", "Глина"),
        conduct_heat=0.15,
        opacity=1.0,
        paintable=True,
        texture=load_texture("Глина")
    ),

    "Мокрый песок": Material(
        name="Мокрый песок",
        color=(169, 153, 103),
        physics_type=(1, 1),
        category=("Строительство", "Песок", 1),
        conduct_heat=0.15,
        opacity=1.0,
        texture=load_texture("Мокрый песок")
    ),

    "Технический мокрый песок": Material(
        name="Мокрый песок",
        color=(169, 153, 103),
        physics_type=(1, 1),
        category=("Секретное", "?"),
        conduct_heat=0.15,
        opacity=1.0,
        texture=load_texture("Мокрый песок")
    ),

    "Твёрдый песок": Material(
        name="Твёрдый песок",
        color=(219, 203, 153),
        physics_type=(0, 0),
        category=("Строительство", "Песок", 2),
        conduct_heat=0.2,
        opacity=1.0,
        texture=load_texture("Плотная пыль")
    ),
    "Кинетический песок": Material(
        name="Кинетический песок",
        color=(255, 105, 180),
        physics_type=(1, 3),
        category=("Строительство", "Песок", 3),
        conduct_heat=0.05,
        conduct_electricity=0.0,
        opacity=1,
        texture=load_texture("Мокрый песок"),
        become_to=(None, None),
        temperature=20,
        heat_capacity=0.8,
        paintable=False
    ),

    "Стекло": Material(
        name="Стекло",
        color=(200, 200, 200),
        physics_type=(0, 0),
        category=("Строительство", "Стекло", 0),
        conduct_heat=0.1,
        opacity=0.6,
        texture=load_texture("Стекло"),
        paintable=True
    ),
    "Осколки стекла": Material(
        name="Песок",
        color=(200, 200, 200),
        physics_type=(1, 0),
        category=("Строительство", "Стекло", 1),
        conduct_heat=0.1,
        opacity=0.85,
        texture=load_texture("Песок")
    ),

    "Инопланетный песок": Material(
        name="Инопланетный песок",
        color=(55, 195, 155),
        physics_type=(1, 2),
        category=("Строительство", "Песок", 4),
        conduct_heat=0.05,
        opacity=1.0,
        texture=load_texture("Песок")
    ),

    "Скала": Material(
        name="Скала",
        color=(70, 70, 70),
        physics_type=(0, 0),
        category=("Строительство", "Скала", 0),
        conduct_heat=0.05,
        conduct_electricity=0.01,
        opacity=1.0,
        texture=load_texture("Скала")
    ),
    "Каменная крошка": Material(
        name="Каменная крошка",
        color=(100, 100, 100),
        physics_type=(1, 0),
        category=("Строительство", "Скала", 1),
        conduct_heat=0.05,
        conduct_electricity=0.01,
        opacity=1.0,
        texture=load_texture("Мокрый песок")
    ),
    "Кирпичная стена": Material(
        name="Кирпичная стена",
        color=(180, 100, 80),
        physics_type=(0, 0),
        category=("Строительство", "Кирпичи"),
        conduct_heat=0.05,
        conduct_electricity=0.01,
        opacity=1.0,
        texture=load_texture("Кирпичная стена"),
        paintable=True

    ),
    "Алмаз": Material(
        name="Алмаз",
        color=(180, 210, 255),
        physics_type=(0, 0),
        category=("Строительство", "Алмаз"),
        conduct_heat=0.05,
        conduct_electricity=0.01,
        opacity=0.6,
        texture=load_texture("Алмаз"),
        glow=False,
        meltable=False,
        freezable=False,
        acid_resistant=True,
        explosive=False,
        temperature=20
    ),
    "Сталь": Material(
        name="Сталь",
        color=(172, 172, 178),
        physics_type=(0, 0),
        category=("Строительство", "Сталь"),
        conduct_heat=0.8,
        conduct_electricity=0.9,
        opacity=1.0,
        texture=load_texture("Сталь"),
        glow=False,
        meltable=True,
        melting_point=1500,
        boiling_point=3000,
        acid_resistant=True,
        explosive=False,
        temperature=20
    ),
    "Доски": Material(
        name="Доски",
        color=(139, 100, 60),
        physics_type=(0, 0),
        category=("Строительство", "Доски", 0),
        conduct_heat=0.2,
        conduct_electricity=0.05,
        flammable=True,
        ignition_point=300,
        meltable=False,
        freezable=False,
        explosive=False,
        acid_resistant=False,
        opacity=1.0,
        texture=load_texture("Доски"),
        paintable=True,
        burn=(0.005, 0.25, 0.25)
    ),
    "Опилки": Material(
        name="Опилки",
        color=(180, 140, 100),
        physics_type=(1, 0),
        category=("Строительство", "Доски", 1),
        conduct_heat=0.1,
        conduct_electricity=0.01,
        flammable=True,
        ignition_point=250,
        acid_resistant=False,
        opacity=1.0,
        texture=load_texture("Мокрый песок"),
        burn=(0.025, 0.15, 0.005)
    ),
    "Бумага": Material(
        name="Бумага",
        color=(240, 240, 220),
        physics_type=(0, 0),
        category=("Строительство", "Бумага"),
        conduct_heat=0.05,
        conduct_electricity=0.01,
        flammable=True,
        ignition_point=230,
        opacity=0.9,
        texture=load_texture("Бумага"),
        paintable=True,
        temperature=20,
        burn=(0.35, 0.45, 0.45)
    ),
    "Уголь": Material(
        name="Уголь",
        color=(37, 37, 37),
        physics_type=(0, 0),
        category=("Строительство", "Уголь"),
        conduct_heat=0.05,
        conduct_electricity=0.0,
        opacity=1.0,
        texture=load_texture("Уголь"),
        flammable=True,
        ignition_point=250,
        burn=(0.00075, 0.0075, 0.05),
        temperature=20,
        heat_capacity=1.2,
        acid_resistant=True,
    ),

    "Вода": Material(
        name="Вода",
        color=(100, 150, 255),
        physics_type=(2, 0),
        category=("Жидкости и газы", "Вода", 0),
        conduct_heat=0.3,
        conduct_electricity=0.05,
        boiling_point=100,
        freezing_point=0,
        opacity=0.8,
        texture=load_texture("Вода"),
        become_to=("Лёд", "Пар"),
        temperature=20,
        heat_capacity=4.18,
    ),
    "Пар": Material(
        name="Пар",
        color=(200, 220, 255),
        physics_type=(3, 0),
        category=("Жидкости и газы", "Вода", 1),
        conduct_heat=0.1,
        conduct_electricity=0.0,
        freezing_point=20,
        opacity=0.7,
        temperature=110,
        texture=load_texture("Пар"),
        become_to=(None, "Вода")
    ),
    "Лёд": Material(
        name="Лёд",
        color=(180, 220, 255),
        physics_type=(0, 0),
        category=("Жидкости и газы", "Вода", 2),
        conduct_heat=0.2,
        opacity=0.9,
        texture=load_texture("Песок"),
        become_to=("Вода", None),
        temperature=-1,
        heat_capacity=2.1,
        melting_point=2,
        meltable=True,
        freezable=False
    ),
    "Жидкий азот": Material(
        name="Жидкий азот",
        color=(160, 200, 240),
        physics_type=(2, 0),
        category=("Жидкости и газы", "Азот", 1),
        conduct_heat=0.05,
        conduct_electricity=0.0,
        boiling_point=-196,
        opacity=0.7,
        texture=load_texture("Вода"),
        become_to=(None, "Азот"),
        temperature=-200,
        heat_capacity=2.0,
        meltable=True,

    ),
    "Азот": Material(
        name="Газообразный азот",
        color=(150, 150, 180),
        physics_type=(3, 0),
        category=("Жидкости и газы", "Азот", 0),
        conduct_heat=0.02,
        conduct_electricity=0.0,
        freezing_point=-196,
        opacity=0.5,
        texture=load_texture("Пар"),
        become_to=("Жидкий азот", None),
        temperature=-190,
        heat_capacity=1.0,
    ),
    "Натрий": Material(
        name="Натрий",
        color=(190, 190, 187),
        physics_type=(0, 0),
        reacts_with={"Вода": "burning_water_reaction"},
        category=("Огнеопасное", "Натрий"),
        conduct_heat=0.9,
        opacity=1.0,
        texture=load_texture("Натрий")
    ),
    "Медь": Material(
        name="Медь",
        color=(185, 115, 50),
        physics_type=(0, 0),
        category=("Строительство", "Медь"),
        conduct_heat=0.95,
        conduct_electricity=0.95,
        opacity=1.0,
        texture=load_texture("Медь"),
        glow=False,
        meltable=True,
        melting_point=1085,
        boiling_point=2562,
        acid_resistant=False,
        explosive=False,
        temperature=20
    ),
    "Творческая граница": Material(
        name="Творческая граница",
        color=(30, 30, 40),
        physics_type=(0, 0),
        category=("Секретное", "Творческая граница"),
        conduct_heat=0,
        opacity=1.0,
        texture=load_texture("Творческая граница")
    ),
    "Камень": Material(
        name="Творческая граница",
        color=(120, 120, 120),
        physics_type=(0, 0),
        category=("Секретное", "Камень"),
        conduct_heat=0.05,
        conduct_electricity=0.01,
        opacity=1.0,
        texture=load_texture("Скала")
    ),
    "Огонь": Material(
        name="Огонь",
        color=(250, 230, 120),
        physics_type=(4, 0),
        category=("Огнеопасное", "Огонь", 0),
        conduct_heat=1.0,
        opacity=1,
        temperature=600,
        heat_capacity=1.0,
    ),

    "Гиперогонь": Material(
        name="Гиперогонь",
        color=(220, 60, 140),
        physics_type=(4, 0),
        category=("Огнеопасное", "Огонь", 1),
        conduct_heat=1.0,
        opacity=1,
        temperature=2000,
        heat_capacity=1.0,
    ),
    "Плитка": Material(
        name="Плитка",
        color=(200, 200, 200),
        physics_type=(0, 0),
        acid_resistant=True,
        conduct_heat=0.2,
        heat_capacity=0.8,
        conduct_electricity=0.0,
        temperature=20,
        texture=load_texture("Плитка"),
        opacity=1.0,
        glow=False,
        category=("Строительство", "Плитка", 0),
        reacts_with={},
        become_to=(),
        paintable=True
    ),

    "Мелкая плитка": Material(
        name="Мелкая плитка",
        color=(200, 200, 200),
        physics_type=(0, 0),
        acid_resistant=True,
        conduct_heat=0.2,
        heat_capacity=0.8,
        conduct_electricity=0.0,
        temperature=20,
        texture=load_texture("Мелкая плитка"),
        opacity=1.0,
        glow=False,
        category=("Строительство", "Плитка", 1),
        reacts_with={},
        become_to=(),
        paintable=True
    ),
    "Аэрогель": Material(
        name="Аэрогель",
        color=(220, 240, 255),
        physics_type=(0, 0),
        category=("Строительство", "Аэрогель"),
        conduct_heat=0.004,
        conduct_electricity=0.0,
        opacity=0.3,
        texture=load_texture("Аэрогель"),
        temperature=20,
        acid_resistant=True,
    ),
}
