import pygame
import settings

class Spritesheet:
    def __init__(self, filename):
        self.sheet = settings.get_image(filename)

    def get_image(self, x, y, w, h):
        rect = pygame.Rect(x, y, w, h)
        image = self.sheet.subsurface(rect).copy()
        filter_color = pygame.Color(settings.SPRITESHEET_FILTER_COLOR)
        with pygame.PixelArray(image) as pixels:
            pixels.replace(filter_color, (0, 0, 0, 0))
        return image

    def get_strip(self, start_x, y, count, w, h):
        frames = []
        for i in range(count):
            frame_x = start_x + (i * w)
            frames.append(self.get_image(frame_x, y, w, h))
        return frames

class Entity:
    def __init__(self):
        self.rect: pygame.Rect = pygame.Rect(0, 0, 10, 10)
        self.dead = False

    def update(self, dt: int): pass
    def handle_event(self, event: pygame.Event, game): pass
    def render(self, screen: pygame.Surface, spritesheets: dict[str, Spritesheet]):
        if settings.DEBUG_MODE: pygame.draw.rect(screen, settings.DEBUG_COLORS.COLOR_1.value, self.rect, width=0)

class Contestant(Entity):
    def __init__(self, max_hp: int = 1, max_shield: int = 1, archetype: settings.Archetype = None, game = None):
        super().__init__()
        self.max_shield: int = max_shield
        self.shield: int = self.max_shield
        self.max_hp: int = max_hp
        self.hp: int = self.max_hp
        self.game = game if game is not None else None
        self.archetype = archetype if archetype is not None else None

    def take_dmg(self, amount: int):
        if self.shield > 0:
            self.shield -= amount
        else:
            self.hp -= amount

        self.hp = max(0, min(self.hp, self.max_hp))
        self.shield = max(0, min(self.shield, self.max_shield))
    
    def heal(self, hp: int = 0, shield: int = 0):
        self.hp += hp
        self.shield += shield
        self.hp = max(0, min(self.hp, self.max_hp))
        self.shield = max(0, min(self.shield, self.max_shield))
