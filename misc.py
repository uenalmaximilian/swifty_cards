import pygame
import math
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
        if amount > 0: settings.get_sound("damage.mp3").play()

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
        if hp == 0 and shield != 0: settings.get_sound("shield.mp3").play()
        elif hp != 0 and shield == 0: settings.get_sound("heal.mp3").play()
        elif hp != 0 and shield != 0: settings.get_sound("heal.mp3").play()

class VFXText:
    def __init__(self, surface, x, y, duration=1.2):
        self.original_surface = surface.convert_alpha()
        self.base_x = x
        self.base_y = y
        self.duration = duration
        self.lifetime = duration
        self.x = x
        self.y = y
        self.current_surface = self.original_surface
        self.alpha = 255
        self.rect = self.current_surface.get_rect(center=(x, y))

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0: return

        progress = 1.0 - (self.lifetime / self.duration)
        pop_duration = 0.15
        if progress < pop_duration:
            pop_progress = progress / pop_duration
            current_scale = 1.4 - (0.4 * pop_progress)
        else:
            current_scale = 1.0

        tilt_speed = 18.0
        tilt_amplitude = 12.0
        current_tilt = (math.sin(progress * tilt_speed) * tilt_amplitude * (1.0 - progress))

        fall_speed = 30.0
        y_offset = progress * fall_speed

        fade_start = 0.6
        if progress > fade_start:
            fade_progress = (progress - fade_start) / (1.0 - fade_start)
            self.alpha = int(255 * (1.0 - fade_progress))
        else:
            self.alpha = 255

        self.current_surface = pygame.transform.rotozoom(self.original_surface, current_tilt, current_scale)
        self.current_surface.set_alpha(self.alpha)
        self.x = self.base_x
        self.y = self.base_y + y_offset
        self.rect = self.current_surface.get_rect(center=(int(self.x), int(self.y)))

    @property
    def dead(self): return self.lifetime <= 0

    def render(self, target_surface):
        if not self.dead: target_surface.blit(self.current_surface, self.rect)