import pygame

FONT = None


def init_font():
    global FONT
    try:
        FONT = pygame.font.Font("assets/SuperDuperPixel.ttf", 32)
    except:
        FONT = pygame.font.SysFont("Arial", 32)


def get_font():
    return FONT


def draw_text(surface, text, x, y):
    font = FONT
    text_surface = font.render(text, True, (255, 255, 255))
    outline_surface = font.render(text, True, (0, 0, 0))

    for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
        surface.blit(outline_surface, (x + dx, y + dy))

    surface.blit(text_surface, (x, y))
