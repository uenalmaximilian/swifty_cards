import pygame
import settings
import misc
import ai
import random

class Card(misc.Entity):
    def __init__(self, pos: pygame.Vector2 = None, card_id: int = None, game = None):
        super().__init__()
        self.pos: pygame.Vector2 = pos if pos is not None else pygame.Vector2(0, 0)
        self.target_pos: pygame.Vector2 = pygame.Vector2(self.pos)
        self.size: tuple[int, int] = (42, 64)
        self.rect: pygame.Rect = pygame.Rect(self.pos.x, self.pos.y, self.size[0], self.size[1])
        self.card_type: dict[str, int] = settings.CardTypes.get_by_id(card_id) if card_id is not None else settings.CardTypes.NONE
        self.sprite: pygame.Surface = None
        self.play_button_image: pygame.Surface = None
        self.discard_button_image: pygame.Surface = None

        self.menu_rect: pygame.Rect = pygame.Rect(0, 0, 42, 48)
        self.play_button_rect: pygame.Rect = pygame.Rect(0, 0, 32, 12)
        self.discard_button_rect: pygame.Rect = pygame.Rect(0, 0, 32, 12)
        self._update_rect_positions()
        self.is_hovered: bool = False

        self.game = game if game is not None else None

    def _update_rect_positions(self):
        self.rect.topleft = (int(self.pos.x), int(self.pos.y))
        menu_x = self.pos.x + (self.size[0] / 2) - (42 / 2)
        menu_y = self.pos.y - 48
        self.menu_rect.topleft = (int(menu_x), int(menu_y))
        button_x = self.pos.x + (self.size[0] / 2) - (32 / 2)
        self.play_button_rect.topleft = (int(button_x), int(self.menu_rect.y + 12 + 7))
        self.discard_button_rect.topleft = (int(button_x), int(self.menu_rect.y + 12 + 21))

    def check_hover(self):
        mouse_pos = pygame.mouse.get_pos()
        hovering_card = self.rect.collidepoint(mouse_pos)
        hovering_menu = self.menu_rect.collidepoint(mouse_pos)
        self.is_hovered = hovering_card or hovering_menu

    def update(self, dt: int):
        speed = 15.0
        lerp_factor = 1.0 - (0.5 ** (speed * dt))
        self.pos = self.pos.lerp(self.target_pos, lerp_factor)
        self._update_rect_positions()

    def handle_event(self, event: pygame.Event, game):
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.play_button_rect.collidepoint(event.pos):
                game.countdown += self.card_type["countd"]
                game.opponent.take_dmg(self.card_type["dmg"])
                game.player.heal(hp=self.card_type["hp"], shield=self.card_type["shield"])
                game.last_card_id = self.card_type["id"]
            self.dead = True

    def render(self, screen: pygame.Surface, spritesheets: dict[str, misc.Spritesheet], hidden: bool = False, scale: float = 1.0):
        if self.sprite is None:
            card_id = self.card_type["id"]
            col = card_id % 10
            row = card_id // 10
            self.sprite = spritesheets["cards"].get_image(col * self.size[0], row * self.size[1], self.size[0], self.size[1])
            self.play_button_image = spritesheets["buttons"].get_image(0, 0, 32, 12)
            self.discard_button_image = spritesheets["buttons"].get_image(32, 0, 32, 12)

        if hidden: target_surface = spritesheets["cards"].get_image(98 % 10 * self.size[0], 98 // 10 * self.size[1], self.size[0], self.size[1])
        else: target_surface = self.sprite

        if scale != 1.0 and target_surface:
            new_w = int(self.size[0] * scale)
            new_h = int(self.size[1] * scale)
            target_surface = pygame.transform.scale(target_surface, (new_w, new_h))

        if self.is_hovered and not hidden:
            if settings.DEBUG_MODE:
                pygame.draw.rect(screen, settings.DEBUG_COLORS.COLOR_1.value, self.menu_rect, width=0)
                pygame.draw.rect(screen, settings.DEBUG_COLORS.COLOR_2.value, self.play_button_rect, width=0)
                pygame.draw.rect(screen, settings.DEBUG_COLORS.COLOR_3.value, self.discard_button_rect, width=0)
            screen.blit(self.play_button_image, self.play_button_rect)
            screen.blit(self.discard_button_image, self.discard_button_rect)

        if settings.DEBUG_MODE: super().render(screen, spritesheets)

        if target_surface: screen.blit(target_surface, self.rect)
        else: super().render(screen, spritesheets)

class Player(misc.Contestant):
    def __init__(self, max_hp: int = 10, max_shield: int = 5, deck: list[Card] = None, hand_size: int = 7, archetype: settings.Archetype = None , game = None):
        super().__init__(max_hp, max_shield, archetype, game)
        self.deck: list[Card] = deck.copy() if deck is not None else []
        self.pile: list[Card] = self.deck.copy()
        self.hand: list[Card] = []
        self.max_hand_size = hand_size
        self.game = game if game is not None else None
        self.turn_timer = 0.0

        self.draw_cards()

    def draw_cards(self):
        random.shuffle(self.pile)
        while len(self.hand) < self.max_hand_size and len(self.pile) > 0:
            drawn_card = self.pile.pop()
            drawn_card.dead = False
            self.hand.append(drawn_card)

    def update(self, dt: int):
        for card in self.hand[:]:
            if card.dead:
                self.pile.append(card)
                self.hand.remove(card)

        if len(self.hand) == 0:
            self.draw_cards()

        if self.game.current_turn == settings.Turns.PLAYER.value:
            self.turn_timer += dt

            if self.turn_timer >= 5.0:
                self.turn_timer = 0.0
                if self.hand:
                    random.choice(self.hand).dead = True
                self.game.turn = settings.Turns.ENEMY.value
        else:
            self.turn_timer = 0.0

        card_gap = 5

        if self.hand:
            total_width = len(self.hand) * self.hand[0].size[0] + (len(self.hand) - 1) * card_gap
            start_x = (settings.SCREEN_WIDTH - total_width) // 2

            for i, card in enumerate(self.hand):
                base_y = settings.SCREEN_HEIGHT - card.size[1] - 10
                hover_offset = 15 if card.is_hovered else 0

                target_x = start_x + i * (card.size[0] + card_gap)
                target_y = base_y - hover_offset
                card.target_pos = pygame.Vector2(target_x, target_y)

                if self.game.current_turn == settings.Turns.PLAYER.value: card.check_hover()
                card.update(dt)

    def handle_event(self, event, game):
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.game.current_turn == settings.Turns.PLAYER.value:
            for card in reversed(self.hand[:]):
                if card.rect.collidepoint(event.pos) or card.menu_rect.collidepoint(event.pos):
                    card.handle_event(event, game)
                    if card.dead: game.turn = settings.Turns.ENEMY.value
                    break

    def render(self, screen: pygame.Surface, spritesheets: dict[str, misc.Spritesheet]):
        for card in self.hand:
            card.render(screen, spritesheets)

class Enemy(misc.Contestant):
    def __init__(self, enemy_id: int = settings.AITypes.NORMAL.value, max_hp: int = 10, max_shield: int = 5, deck: list[Card] = None, hand_size: int = 7, archetype: settings.Archetype = None, game = None):
        super().__init__(max_hp, max_shield, archetype, game)
        self.deck: list[Card] = deck.copy() if deck is not None else []
        self.pile: list[Card] = self.deck.copy()
        self.hand: list[Card] = []
        self.max_hand_size = hand_size
        self.game = game if game is not None else None

        self.model: ai.Model = ai.AI_REGISTRY.get(enemy_id, ai.Normal())
        self.timer = 0.0

        self.draw_cards()

    def draw_cards(self):
        random.shuffle(self.pile)
        while len(self.hand) < self.max_hand_size and len(self.pile) > 0:
            drawn_card = self.pile.pop()
            drawn_card.dead = False
            self.hand.append(drawn_card)

    def play_card(self):
        if not self.hand: return

        chosen_card, action = self.model.choose_card(self.hand, self, self.game)

        if action == "play":
            self.game.countdown += chosen_card.card_type["countd"]
            self.game.player.take_dmg(chosen_card.card_type["dmg"])
            self.heal(hp=chosen_card.card_type["hp"], shield=chosen_card.card_type["shield"])
            self.game.last_card_id = chosen_card.card_type["id"]
        self.game.turn = settings.Turns.PLAYER.value
        chosen_card.dead = True

    def update(self, dt: int):
        for card in self.hand[:]:
            if card.dead:
                self.pile.append(card)
                self.hand.remove(card)

        if len(self.hand) == 0:
            self.draw_cards()

        if self.game.current_turn == settings.Turns.ENEMY.value:
            self.timer += dt
            if self.timer >= round(random.uniform(0.5, 2.0), 1):
                self.play_card()
                self.timer = 0.0
        else:
            self.timer = 0.0

        card_gap = 5
        small_width = 42 * 0.5
        small_height = 64 * 0.5

        if self.hand:
            total_width = len(self.hand) * small_width + (len(self.hand) - 1) * card_gap
            start_x = (settings.SCREEN_WIDTH - total_width) // 2

            for i, card in enumerate(self.hand):
                card.rect.size = (small_width, small_height)

                base_y = small_height - 5
                target_x = start_x + i * (small_width + card_gap)
                target_y = base_y
                
                card.target_pos = pygame.Vector2(target_x, target_y)
                card.update(dt)

    def render(self, screen: pygame.Surface, spritesheets: dict[str, misc.Spritesheet]):
        for card in self.hand:
            card.render(screen, spritesheets, hidden=True, scale=0.5)