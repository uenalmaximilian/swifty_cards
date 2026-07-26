import pygame
import settings
import misc
import cards
import random
import math
import sys
import asyncio

class Game:
    def __init__(self, entities: list[misc.Entity] = None):
        if sys.platform == "emscripten":
            self.screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
            import platform
            platform.window.eval('document.getElementById("canvas").style.imageRendering = "pixelated";')
        else: self.screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SCALED)
        self.surface = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
        pygame.display.set_caption("Swifty Cards")
        pygame.display.set_icon(settings.get_image("icon.png"))
        self.clock = pygame.time.Clock()
        self.font = settings.get_font("consolas-regular.ttf", 21)
        self.title_font = settings.get_font("consolas-bold.ttf", 32)
        self.contestant_font = settings.get_font("consolas-regular.ttf", 16)

        self.spritesheets = {
            "cards": misc.Spritesheet("cards.png"),
            "buttons": misc.Spritesheet("buttons.png"),
            "archetypes": misc.Spritesheet("archetypes.png"),
            "misc": misc.Spritesheet("misc.png"),
            "pictures": misc.Spritesheet("pictures.png")
        }
        self.entities = entities if entities is not None else []

        self.delta_time = 0
        self.running = False
        self.state = settings.GameState.MAINMENU.value
        self.score = 0
        self.last_action: settings.Actions = None
        self.active_vfx: list[misc.VFXText] = []

        self.draft_rects: list[pygame.Rect] = []
        self.draft_options: list[cards.Card] = []
        self.draft_skip_rect: pygame.Rect = None
        self.menu_start_rect: pygame.Rect = None
        self.game_over_button_rect: pygame.Rect = None
        self.pause_button_rect: pygame.Rect = None
        self.pause_menu_button_rect: pygame.Rect = None
        self.archetype_menu_rects: list[tuple[pygame.Rect, settings.Archetype]] = []
        self.settings_menu_rect: pygame.Rect = None
        self.back_rect: pygame.Rect = None
        self.fullscreen_rect: pygame.Rect = None
        self.stat_menu_rect: pygame.Rect = None
        self.stat_hp_rect: pygame.Rect = None
        self.stat_shield_rect: pygame.Rect = None
        self.quit_rect: pygame.Rect = None
        self.wipe_data_rect: pygame.Rect = None
        self.pause_rect: pygame.Rect = None
        self.sfx_slider_rect: pygame.Rect = None
        self.music_slider_rect: pygame.Rect = None

        self.in_transition = False
        self.transition_timer = 0.0
        self.fade_alpha = 0.0
        self.transition_step = None
        self.next_state = None

        self.is_fullscreen = False

        self.gamesave = settings.load_game()
        settings.sfx_volume = self.gamesave["sfx"]
        settings.get_sound("start.ogg").play()
        settings.get_music("music_1.ogg")
        pygame.mixer.music.set_volume(self.gamesave["music"])
        pygame.mixer.music.play(-1)

    def toggle_fullscreen(self):
        if sys.platform == "emscripten":
            import platform
            platform.window.eval('''
                var canvas = document.getElementById("canvas");
                if (!document.fullscreenElement) {
                    if (canvas.requestFullscreen) { canvas.requestFullscreen(); }
                    else if (canvas.webkitRequestFullscreen) { canvas.webkitRequestFullscreen(); }
                } else {
                    if (document.exitFullscreen) { document.exitFullscreen(); }
                }
            ''')
        else:
            self.is_fullscreen = not self.is_fullscreen
            if self.is_fullscreen: self.screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SCALED | pygame.FULLSCREEN)
            else: self.screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SCALED)

    def trigger_transition(self, next_state, freeze_time=0.15):
        self.active_vfx.clear()
        self.in_transition = True
        self.transition_timer = freeze_time
        self.transition_step = settings.TransitionStep.FREEZE.value
        self.next_state = next_state
        self.fade_alpha = 0.0

    def new_game(self, chosen_archetype: settings.Archetype = settings.Archetype.BALANCED):
        self.score = 0

        deck_data = settings.Decks[chosen_archetype.name].value

        deck = []
        for card_data in deck_data["deck"]:
            card = cards.Card(None, card_data["id"], self)
            deck.append(card)
        random.shuffle(deck)

        self.player: cards.Player = cards.Player(max_hp=(deck_data["hp"] + self.gamesave["hp_stat"]), max_shield=(deck_data["shield"] + self.gamesave["shield_stat"]), deck=deck, hand_size=7, archetype=chosen_archetype, game=self)
        self.new_match()

    def new_match(self):
        self.active_vfx.clear()
        self.countdown = 30.0
        self.last_card_id = 0
        self.entities.clear()
        self.player.turn_timer = 0.0
        self.trigger_transition(settings.GameState.PLAYING.value)

        self.player.hp = self.player.max_hp
        self.player.shield = self.player.max_shield
        self.player.hand.clear()
        self.player.pile = self.player.deck.copy()
        self.player.draw_cards()

        archetype = random.choice(list(settings.Archetype))
        deck_data = settings.Decks[archetype.name].value

        deck = []
        for card_data in deck_data["deck"]:
            card = cards.Card(None, card_data["id"], self)
            deck.append(card)

        for _ in range(self.score):
            random_id = random.randint(1, settings.MAX_CARD_ID)
            deck.append(cards.Card(None, random_id, self))

        random.shuffle(deck)

        enemy_max_hp = deck_data["hp"] + (random.randint(1, 3) * self.score)
        enemy_max_shield = deck_data["shield"] + (random.randint(1, 2) * self.score)

        self.opponent: cards.Enemy = cards.Enemy(max_hp=enemy_max_hp, max_shield=enemy_max_shield, deck=deck, hand_size=7, archetype=archetype, game=self)
        self.opponent.hp = self.opponent.max_hp
        self.opponent.shield = self.opponent.max_shield
        self.opponent.hand.clear()
        self.opponent.pile = self.opponent.deck.copy()
        self.opponent.draw_cards()
        if random.random() < 0.01: self.opponent.id = random.randint(settings.SECRET_ENEMY_ID_START, settings.MAX_SECRET_ENEMY_ID)
        else: self.opponent.id = random.randint(settings.ENEMY_START_ID, settings.MAX_ENEMY_ID)

        self.current_turn: int = settings.Turns.PLAYER.value
        self.turn: int = self.current_turn

        self.entities.append(self.player)
        self.entities.append(self.opponent)

    def update(self):
        if self.in_transition:
            if self.transition_step == settings.TransitionStep.FREEZE.value:
                self.transition_timer -= self.delta_time
                if self.transition_timer <= 0:
                    self.transition_step = settings.TransitionStep.FADEOUT.value

            elif self.transition_step == settings.TransitionStep.FADEOUT.value:
                self.fade_alpha += 800 * self.delta_time
                if self.fade_alpha >= 255:
                    self.fade_alpha = 255
                    if self.next_state == settings.GameState.DRAFTING.value:
                        self.setup_draft()
                    self.state = self.next_state

                    self.transition_timer = 0.5
                    self.transition_step = settings.TransitionStep.HOLD.value

            elif self.transition_step == settings.TransitionStep.HOLD.value:
                self.transition_timer -= self.delta_time
                if self.transition_timer <= 0:
                    self.transition_step = settings.TransitionStep.FADEIN.value

            elif self.transition_step == settings.TransitionStep.FADEIN.value:
                self.fade_alpha -= 800 * self.delta_time
                if self.fade_alpha <= 0:
                    self.fade_alpha = 0
                    self.in_transition = False

            return

        if self.state == settings.GameState.PLAYING.value:
            self.countdown -= self.delta_time

            for obj in self.entities[:]:
                obj.update(self.delta_time)
            self.entities = [e for e in self.entities if not e.dead]

            if self.turn != self.current_turn:
                if self.last_action.name == "DUMPED": vfx_string = f"{self.last_action.name.lower().title()}"
                else:
                    vfx_string = ""
                    for attr, value in settings.CardTypes.get_by_id(self.last_card_id).items():
                        string_dict = {"countd": "Time", "dmg": "Damage", "hp": "HP", "shield": "Shield"}
                        if attr != "id" and value != 0:
                            vfx_string += f"{"+" if value > 0 else ""}{value} {string_dict[attr]}\n"
                vfx_text = self.contestant_font.render(f"{vfx_string.strip()}!", False, (200, 200, 200))
                if self.current_turn == settings.Turns.PLAYER.value: vfx_x, vfx_y = 53, 103
                else: vfx_x, vfx_y = 427, 103
                self.active_vfx.append(misc.VFXText(surface=vfx_text, x=vfx_x, y=vfx_y, duration=1.0))
                self.current_turn = self.turn

            for vfx in self.active_vfx[:]:
                vfx.update(self.delta_time)
            self.active_vfx = [vfx for vfx in self.active_vfx if not vfx.dead]

            if self.player.hp < 1:
                if self.score > self.gamesave["highscore"]: self.gamesave["highscore"] = self.score
                settings.get_sound("lose.ogg").play()
                self.trigger_transition(settings.GameState.GAMEOVER.value, 1.0)
            if self.opponent.hp < 1:
                self.score += 1
                self.gamesave["stat_points"] += 1
                self.gamesave["gold"] += random.randint(1, 3)
                self.setup_draft()
                settings.get_sound("win.ogg").play()
                self.trigger_transition(settings.GameState.DRAFTING.value, 0.5)

            if self.countdown <= 0.0:
                if self.current_turn == settings.Turns.PLAYER.value:
                    if self.score > self.gamesave["highscore"]: self.gamesave["highscore"] = self.score
                    settings.get_sound("lose.ogg").play()
                    self.trigger_transition(settings.GameState.GAMEOVER.value, 1.0)
                elif self.current_turn == settings.Turns.ENEMY.value:
                    self.score += 1
                    self.gamesave["stat_points"] += 1
                    self.gamesave["gold"] += random.randint(1, 3)
                    self.setup_draft()
                    settings.get_sound("win.ogg").play()
                    self.trigger_transition(settings.GameState.DRAFTING.value, 0.5)

    def render(self):
        if self.state == settings.GameState.MAINMENU.value: self.render_main_menu()
        elif self.state == settings.GameState.DRAFTING.value: self.render_draft()
        elif self.state == settings.GameState.ARCHETYPECHOOSING.value: self.render_archetype_menu()
        elif self.state == settings.GameState.SETTINGSMENU.value: self.render_settings_menu()
        elif self.state == settings.GameState.STATMENU.value: self.render_stat_menu()
        elif self.state in (settings.GameState.PLAYING.value, settings.GameState.PAUSED.value, settings.GameState.GAMEOVER.value):
            self.render_gameplay()
            if self.state == settings.GameState.PAUSED.value: self.render_pause_overlay()
            elif self.state == settings.GameState.GAMEOVER.value: self.render_game_over()
        if self.fade_alpha > 0:
            fade_surface = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
            fade_surface.fill((0, 0, 0, int(self.fade_alpha)))
            self.surface.blit(fade_surface, (0, 0))

    def render_main_menu(self):
        current_time = pygame.time.get_ticks()
        y_offset = math.sin(current_time * 0.001) * 10

        title = self.title_font.render("SWIFTY CARDS", False, "#EBEBEB")

        base_y_title = settings.SCREEN_HEIGHT // 2 - 20

        self.surface.fill((10, 10, 10))
        self.surface.blit(title, title.get_rect(center=(settings.SCREEN_WIDTH // 2, base_y_title + y_offset)))

        highscore_text = self.font.render(f"High Score: {self.gamesave["highscore"]}", False, (230, 230, 230))
        self.surface.blit(highscore_text, highscore_text.get_rect(bottomleft=(5, settings.SCREEN_HEIGHT)))

        btn_w, btn_h = 96, 36
        btn_x = settings.SCREEN_WIDTH // 2
        btn_y = settings.SCREEN_HEIGHT // 2 + 30
        self.menu_start_rect = pygame.Rect(0, 0, btn_w, btn_h)
        self.menu_start_rect.center = (btn_x, btn_y)
        if settings.DEBUG_MODE: pygame.draw.rect(self.surface, settings.DEBUG_COLORS.COLOR_7.value, self.menu_start_rect, width=0)
        menu_start_image = self.spritesheets["buttons"].get_image(64, 0, 32, 12)
        scaled_image = pygame.transform.scale(menu_start_image, (btn_w, btn_h))
        self.surface.blit(scaled_image, self.menu_start_rect)

        btn_w, btn_h = 96, 36
        btn_x = settings.SCREEN_WIDTH // 2
        btn_y = self.menu_start_rect.bottom + 25
        self.stat_menu_rect = pygame.Rect(0, 0, btn_w, btn_h)
        self.stat_menu_rect.center = (btn_x, btn_y)
        if settings.DEBUG_MODE: pygame.draw.rect(self.surface, settings.DEBUG_COLORS.COLOR_7.value, self.stat_menu_rect, width=0)
        stat_menu_image = self.spritesheets["buttons"].get_image(256, 0, 32, 12)
        scaled_image = pygame.transform.scale(stat_menu_image, (btn_w, btn_h))
        self.surface.blit(scaled_image, self.stat_menu_rect)

        btn_w, btn_h = 110, 26
        btn_x = settings.SCREEN_WIDTH // 2
        btn_y = self.stat_menu_rect.bottom + 20
        self.settings_menu_rect = pygame.Rect(0, 0, btn_w, btn_h)
        self.settings_menu_rect.center = (btn_x, btn_y)
        if settings.DEBUG_MODE: pygame.draw.rect(self.surface, settings.DEBUG_COLORS.COLOR_7.value, self.settings_menu_rect, width=0)
        settings_menu_image = self.spritesheets["misc"].get_image(73, 0, 55, 13)
        scaled_image = pygame.transform.scale(settings_menu_image, (btn_w, btn_h))
        self.surface.blit(scaled_image, self.settings_menu_rect)

        if sys.platform != "emscripten":
            btn_w, btn_h = 64, 24
            self.quit_rect = pygame.Rect(0, 0, btn_w, btn_h)
            self.quit_rect.topright = (settings.SCREEN_WIDTH - 5, 5)
            if settings.DEBUG_MODE: pygame.draw.rect(self.surface, settings.DEBUG_COLORS.COLOR_7.value, self.quit_rect, width=0)
            quit_button_image = self.spritesheets["buttons"].get_image(288, 0, 32, 12)
            scaled_image = pygame.transform.scale(quit_button_image, (btn_w, btn_h))
            self.surface.blit(scaled_image, self.quit_rect)

            mouse_pos = pygame.mouse.get_pos()
            if self.quit_rect.collidepoint(mouse_pos):
                tooltip_text = self.contestant_font.render("pls dont quit :(", False, (230, 230, 230))
                tooltip_text_rect = tooltip_text.get_rect()
                tooltip_rect = pygame.Rect(0, 0, tooltip_text_rect.width, tooltip_text_rect.height)
                tooltip_rect.topright = mouse_pos
                pygame.draw.rect(self.surface, (20, 20, 20), tooltip_rect, width=0)
                self.surface.blit(tooltip_text, tooltip_rect)

    def render_stat_menu(self):
        self.surface.fill((10, 10, 10))

        title = self.title_font.render("Stats", False, (230, 230, 230))
        self.surface.blit(title, title.get_rect(center=(settings.SCREEN_WIDTH // 2, 50)))

        stat_points_text = self.font.render(f"Stat points: {self.gamesave["stat_points"]}", False, (230, 230, 230))
        self.surface.blit(stat_points_text, stat_points_text.get_rect(topright=(settings.SCREEN_WIDTH - 5, 5)))

        btn_w, btn_h = 32 * 2, 12 * 2
        self.back_rect = pygame.Rect(5, 5, btn_w, btn_h)
        if settings.DEBUG_MODE: pygame.draw.rect(self.surface, settings.DEBUG_COLORS.COLOR_5.value, self.back_rect, width=0)
        back_button_image = self.spritesheets["buttons"].get_image(224, 0, 32, 12)
        scaled_image = pygame.transform.scale(back_button_image, (btn_w, btn_h))
        self.surface.blit(scaled_image, self.back_rect)

        btn_w, btn_h = 46 * 2, 13 * 2
        btn_x = settings.SCREEN_WIDTH // 2
        btn_y = settings.SCREEN_HEIGHT // 2 - 40
        self.stat_hp_rect = pygame.Rect(0, 0, btn_w, btn_h)
        self.stat_hp_rect.center = (btn_x, btn_y)
        if settings.DEBUG_MODE: pygame.draw.rect(self.surface, settings.DEBUG_COLORS.COLOR_1.value, self.stat_hp_rect, width=0)
        hp_button_image = self.spritesheets["misc"].get_image(0, 13, 46, 13)
        scaled_image = pygame.transform.scale(hp_button_image, (btn_w, btn_h))
        self.surface.blit(scaled_image, self.stat_hp_rect)

        btn_w, btn_h = 40 * 2, 13 * 2
        btn_x = settings.SCREEN_WIDTH // 2
        btn_y = settings.SCREEN_HEIGHT // 2
        self.stat_shield_rect = pygame.Rect(0, 0, btn_w, btn_h)
        self.stat_shield_rect.center = (btn_x, btn_y)
        if settings.DEBUG_MODE: pygame.draw.rect(self.surface, settings.DEBUG_COLORS.COLOR_1.value, self.stat_shield_rect, width=0)
        shield_button_image = self.spritesheets["misc"].get_image(46, 13, 40, 13)
        scaled_image = pygame.transform.scale(shield_button_image, (btn_w, btn_h))
        self.surface.blit(scaled_image, self.stat_shield_rect)

        mouse_pos = pygame.mouse.get_pos()
        if self.stat_hp_rect.collidepoint(mouse_pos):
            tooltip_text = self.font.render(f"HP Bonus: +{self.gamesave["hp_stat"]}", False, (230, 230, 230))
            tooltip_text_rect = tooltip_text.get_rect()
            tooltip_rect = pygame.Rect(0, 0, tooltip_text_rect.width, tooltip_text_rect.height)
            tooltip_rect.bottomleft = mouse_pos
            pygame.draw.rect(self.surface, (20, 20, 20), tooltip_rect, width=0)
            self.surface.blit(tooltip_text, tooltip_rect)
        elif self.stat_shield_rect.collidepoint(mouse_pos):
            tooltip_text = self.font.render(f"Shield Bonus: +{self.gamesave["shield_stat"]}", False, (230, 230, 230))
            tooltip_text_rect = tooltip_text.get_rect()
            tooltip_rect = pygame.Rect(0, 0, tooltip_text_rect.width, tooltip_text_rect.height)
            tooltip_rect.bottomleft = mouse_pos
            pygame.draw.rect(self.surface, (20, 20, 20), tooltip_rect, width=0)
            self.surface.blit(tooltip_text, tooltip_rect)

    def render_settings_menu(self):
        self.surface.fill((10, 10, 10))

        title = self.title_font.render("Settings", False, (230, 230, 230))
        self.surface.blit(title, title.get_rect(center=(settings.SCREEN_WIDTH // 2, 50)))

        btn_w, btn_h = 32 * 2, 12 * 2
        self.back_rect = pygame.Rect(5, 5, btn_w, btn_h)
        if settings.DEBUG_MODE: pygame.draw.rect(self.surface, settings.DEBUG_COLORS.COLOR_5.value, self.back_rect, width=0)
        back_button_image = self.spritesheets["buttons"].get_image(224, 0, 32, 12)
        scaled_image = pygame.transform.scale(back_button_image, (btn_w, btn_h))
        self.surface.blit(scaled_image, self.back_rect)

        btn_w, btn_h = 73 * 2, 13 * 2
        btn_x = settings.SCREEN_WIDTH // 2
        btn_y = settings.SCREEN_HEIGHT // 2
        self.fullscreen_rect = pygame.Rect(0, 0, btn_w, btn_h)
        self.fullscreen_rect.center = (btn_x, btn_y)
        if settings.DEBUG_MODE: pygame.draw.rect(self.surface, settings.DEBUG_COLORS.COLOR_5.value, self.fullscreen_rect, width=0)
        fullscreen_button_image = self.spritesheets["misc"].get_image(0, 0, 73, 13)
        scaled_image = pygame.transform.scale(fullscreen_button_image, (btn_w, btn_h))
        self.surface.blit(scaled_image, self.fullscreen_rect)

        mouse_pos = pygame.mouse.get_pos()
        mouse = pygame.mouse.get_pressed()

        step_size = 0.05
        slider_w, slider_h = 100, 24
        slider_container_rect = pygame.Rect(0, 0, slider_w, slider_h)
        slider_container_rect.center = (settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2 + 40)
        min_x = (slider_container_rect.left + 12)
        max_x = (slider_container_rect.right - 12)
        slider_range = max_x - min_x
        pygame.draw.rect(self.surface, "#1D156B", slider_container_rect, width=0, border_radius=10)
        if not self.sfx_slider_rect:
            self.sfx_slider_rect = pygame.Rect(slider_container_rect.x, slider_container_rect.y, 24, 24)
            self.sfx_slider_rect.centerx = min_x + (self.gamesave["sfx"] * slider_range)
        pygame.draw.rect(self.surface, "#4B3AE2", self.sfx_slider_rect, width=0, border_radius=10)
        pygame.draw.rect(self.surface, "#DBDBDB", self.sfx_slider_rect, width=2, border_radius=10)
        text = self.font.render("SFX ", False, (230, 230, 230))
        self.surface.blit(text, text.get_rect(midright=(slider_container_rect.midleft)))
        if slider_container_rect.collidepoint(mouse_pos) and mouse[0]:
            clamped_val = min(max(0.0, (mouse_pos[0] - min_x) / slider_range), 1.0)
            self.gamesave["sfx"] = round(clamped_val / step_size) * step_size
            settings.sfx_volume = self.gamesave["sfx"]
            self.sfx_slider_rect.centerx = min_x + (self.gamesave["sfx"] * slider_range)

        slider_container_rect = pygame.Rect(0, 0, slider_w, slider_h)
        slider_container_rect.center = (settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2 + 70)
        pygame.draw.rect(self.surface, "#1D156B", slider_container_rect, width=0, border_radius=10)
        if not self.music_slider_rect:
            self.music_slider_rect = pygame.Rect(slider_container_rect.x, slider_container_rect.y, 24, 24)
            self.music_slider_rect.centerx = min_x + (self.gamesave["music"] * slider_range)
        pygame.draw.rect(self.surface, "#4B3AE2", self.music_slider_rect, width=0, border_radius=10)
        pygame.draw.rect(self.surface, "#DBDBDB", self.music_slider_rect, width=2, border_radius=10)
        text = self.font.render("Music ", False, (230, 230, 230))
        self.surface.blit(text, text.get_rect(midright=(slider_container_rect.midleft)))
        if slider_container_rect.collidepoint(mouse_pos) and mouse[0]:
            clamped_val = min(max(0.0, (mouse_pos[0] - min_x) / slider_range), 1.0)
            self.gamesave["music"] = round(clamped_val / step_size) * step_size
            pygame.mixer.music.set_volume(self.gamesave["music"])
            self.music_slider_rect.centerx = min_x + (self.gamesave["music"] * slider_range)

        if sys.platform != "emscripten":
            btn_w, btn_h = 32 * 2, 12 * 2
            self.wipe_data_rect = pygame.Rect(0, 0, btn_w, btn_h)
            self.wipe_data_rect.center = (settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT - 20)
            if settings.DEBUG_MODE: pygame.draw.rect(self.surface, settings.DEBUG_COLORS.COLOR_5.value, self.wipe_data_rect, width=0)
            wipe_button_image = self.spritesheets["buttons"].get_image(0, 12, 32, 12)
            scaled_image = pygame.transform.scale(wipe_button_image, (btn_w, btn_h))
            self.surface.blit(scaled_image, self.wipe_data_rect)

            if self.wipe_data_rect.collidepoint(mouse_pos):
                tooltip_text = self.contestant_font.render("THIS WILL WIPE YOUR ONE AND\nONLY GAME SAVE INSTANTLY!\nONLY CLICK IF YOU ARE SURE!", False, (230, 230, 230))
                tooltip_text_rect = tooltip_text.get_rect()
                tooltip_rect = pygame.Rect(0, 0, tooltip_text_rect.width, tooltip_text_rect.height)
                tooltip_rect.bottomleft = mouse_pos
                tooltip_rect.centerx = mouse_pos[0]
                pygame.draw.rect(self.surface, (20, 20, 20), tooltip_rect, width=0)
                self.surface.blit(tooltip_text, tooltip_rect)

    def render_archetype_menu(self):
        self.surface.fill((10, 10, 25))

        self.archetype_menu_rects.clear()

        title = self.title_font.render("Archetypes", False, (230, 230, 230))
        self.surface.blit(title, title.get_rect(center=(settings.SCREEN_WIDTH // 2, 50)))

        btn_w, btn_h = 32 * 2, 12 * 2
        self.back_rect = pygame.Rect(5, 5, btn_w, btn_h)
        if settings.DEBUG_MODE: pygame.draw.rect(self.surface, settings.DEBUG_COLORS.COLOR_5.value, self.back_rect, width=0)
        back_button_image = self.spritesheets["buttons"].get_image(224, 0, 32, 12)
        scaled_image = pygame.transform.scale(back_button_image, (btn_w, btn_h))
        self.surface.blit(scaled_image, self.back_rect)

        archetypes_list = list(settings.Archetype)
        btn_w, btn_h = 48, 64
        spacing = 30
        total_width = len(archetypes_list) * btn_w + (len(archetypes_list) - 1) * spacing

        start_x = (settings.SCREEN_WIDTH - total_width) // 2
        btn_y = settings.SCREEN_HEIGHT // 2 - (btn_h // 2)

        active_tooltip = None

        for i, archetype in enumerate(archetypes_list):
            btn_x = start_x + i * (btn_w + spacing)
            rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
            self.archetype_menu_rects.append((rect, archetype))
            if settings.DEBUG_MODE: pygame.draw.rect(self.surface, settings.DEBUG_COLORS.COLOR_3.value, rect, width=0)
            archetype_image = self.spritesheets["archetypes"].get_image(i % 10 * btn_w, i // 10 * btn_h, btn_w, btn_h)
            self.surface.blit(archetype_image, rect)

            mouse_pos = pygame.mouse.get_pos()
            if rect.collidepoint(mouse_pos):
                active_tooltip = archetype

        if active_tooltip:
            tooltip_text = self.font.render(f"{active_tooltip.name.lower().title()}\n{settings.DeckStrings[active_tooltip.name].value}", False, (230, 230, 230))
            tooltip_text_rect = tooltip_text.get_rect()
            tooltip_rect = pygame.Rect(0, 0, tooltip_text_rect.width, tooltip_text_rect.height)
            tooltip_rect.bottomleft = mouse_pos
            overflow_top = tooltip_rect.top < 0
            if overflow_top: tooltip_rect.topleft = mouse_pos
            if tooltip_rect.bottom > settings.SCREEN_HEIGHT:
                if overflow_top: tooltip_rect.centery = mouse_pos[1]
                else: tooltip_rect.bottom = mouse_pos[1]
            overflow_right = tooltip_rect.right > settings.SCREEN_WIDTH
            if overflow_right: tooltip_rect.right = mouse_pos[0]
            pygame.draw.rect(self.surface, (20, 20, 20), tooltip_rect, width=0)
            self.surface.blit(tooltip_text, tooltip_rect)

    def render_gameplay(self):
        self.surface.fill((10, 10, 10))

        for obj in self.entities:
            obj.render(self.surface, self.spritesheets)

        last_card_image = self.spritesheets["cards"].get_image(self.last_card_id % 10 * 42, self.last_card_id // 10 * 64, 42, 64) if self.last_card_id is not None else None
        self.surface.blit(last_card_image, (settings.SCREEN_WIDTH // 2 - 21, settings.SCREEN_HEIGHT // 2 - 52))

        color = (255, 255, 255) if self.countdown > 5.0 else (255, 50, 50)
        countdown_text = self.font.render(f"{max(0.0, self.countdown):.2f}", False, color)
        countdown_rect = countdown_text.get_rect()
        countdown_rect.center = (settings.SCREEN_WIDTH // 2, 16)
        self.surface.blit(countdown_text, countdown_rect)

        if self.player.turn_timer >= 2.0:
            turn_timer_text = self.contestant_font.render(f"{max(0.0, 5.0 - self.player.turn_timer):.2f}", False, (255, 50, 50))
            self.surface.blit(turn_timer_text, turn_timer_text.get_rect(center=(settings.SCREEN_WIDTH // 2, 74)))

        for vfx in self.active_vfx: vfx.render(self.surface)

        btn_w, btn_h = 40 * 1.5, 13 * 1.5
        self.pause_rect = pygame.Rect(0, 0, btn_w, btn_h)
        self.pause_rect.bottomleft = (5, settings.SCREEN_HEIGHT - 5)
        if settings.DEBUG_MODE: pygame.draw.rect(self.surface, settings.DEBUG_COLORS.COLOR_5.value, self.pause_rect, width=0)
        pause_button_image = self.spritesheets["misc"].get_image(0, 26, 40, 13)
        scaled_image = pygame.transform.scale(pause_button_image, (btn_w, btn_h))
        self.surface.blit(scaled_image, self.pause_rect)

        player_image_rect = pygame.Rect(3, 3, 32, 32)
        if settings.DEBUG_MODE: pygame.draw.rect(self.surface, settings.DEBUG_COLORS.COLOR_2.value, player_image_rect, width=0)
        player_image = self.spritesheets["pictures"].get_image(0, 0, 16, 16)
        scaled_image = pygame.transform.scale(player_image, (32, 32))
        self.surface.blit(scaled_image, player_image_rect)
        enemy_image_rect = pygame.Rect(settings.SCREEN_WIDTH - 35, 3, 32, 32)
        if settings.DEBUG_MODE: pygame.draw.rect(self.surface, settings.DEBUG_COLORS.COLOR_1.value, enemy_image_rect, width=0)
        enemy_image = self.spritesheets["pictures"].get_image(self.opponent.id % 10 * 16, self.opponent.id // 10 * 16, 16, 16)
        scaled_image = pygame.transform.scale(enemy_image, (32, 32))
        self.surface.blit(scaled_image, enemy_image_rect)

        player_max_hp_rect = pygame.Rect(3, player_image_rect.height + 6, (self.player.max_hp / self.player.max_hp) * 100, 14)
        pygame.draw.rect(self.surface, "#007F00", player_max_hp_rect, width=0, border_radius=3)
        player_hp_progress = round((self.player.hp / self.player.max_hp) * 100)
        player_hp_rect = pygame.Rect(3, player_image_rect.height + 6, player_hp_progress, 14)
        pygame.draw.rect(self.surface, "#00FF00", player_hp_rect, width=0, border_radius=3)
        player_hp_text = self.contestant_font.render(f"{self.player.hp} / {self.player.max_hp}", False, (230, 230, 230))
        text_rect = player_hp_text.get_rect()
        text_rect.center = player_max_hp_rect.center
        text_rect.y += 2
        self.surface.blit(player_hp_text, text_rect)

        player_max_shield_rect = pygame.Rect(3, player_image_rect.height + player_max_hp_rect.height + 9, (self.player.max_shield / self.player.max_shield) * 100, 14)
        pygame.draw.rect(self.surface, "#00557F", player_max_shield_rect, width=0, border_radius=3)
        player_shield_progress = round((self.player.shield / self.player.max_shield) * 100)
        player_shield_rect = pygame.Rect(3, player_image_rect.height + player_max_hp_rect.height + 9, player_shield_progress, 14)
        pygame.draw.rect(self.surface, "#00AAFF", player_shield_rect, width=0, border_radius=3)
        player_shield_text = self.contestant_font.render(f"{self.player.shield} / {self.player.max_shield}", False, (230, 230, 230))
        text_rect = player_shield_text.get_rect()
        text_rect.center = player_max_shield_rect.center
        text_rect.y += 2
        self.surface.blit(player_shield_text, text_rect)
        player_text = self.contestant_font.render(f"{self.player.archetype.name.lower().title()}", False, (230, 230, 230))
        archetype_rect = player_text.get_rect()
        archetype_rect.midtop = (player_max_shield_rect.centerx, player_max_shield_rect.bottom + 4)
        self.surface.blit(player_text, archetype_rect)

        total_enemy_bar_width = (self.opponent.max_hp / self.opponent.max_hp) * 100
        enemy_max_hp_rect = pygame.Rect(settings.SCREEN_WIDTH - 3 - total_enemy_bar_width, enemy_image_rect.height + 6, total_enemy_bar_width, 14)
        pygame.draw.rect(self.surface, "#7F0000", enemy_max_hp_rect, width=0, border_radius=3)
        enemy_hp_progress = round((self.opponent.hp / self.opponent.max_hp) * 100)
        enemy_hp_rect = pygame.Rect(settings.SCREEN_WIDTH - 3 - total_enemy_bar_width, enemy_image_rect.height + 6, enemy_hp_progress, 14)
        pygame.draw.rect(self.surface, "#FF0000", enemy_hp_rect, width=0, border_radius=3)
        enemy_hp_text = self.contestant_font.render(f"{self.opponent.hp} / {self.opponent.max_hp}", False, (230, 230, 230))
        text_rect = enemy_hp_text.get_rect()
        text_rect.center = enemy_max_hp_rect.center
        text_rect.y += 2
        self.surface.blit(enemy_hp_text, text_rect)

        enemy_max_shield_rect = pygame.Rect(settings.SCREEN_WIDTH - 3 - total_enemy_bar_width, enemy_image_rect.height + enemy_max_hp_rect.height + 9, total_enemy_bar_width, 14)
        pygame.draw.rect(self.surface, "#00007F", enemy_max_shield_rect, width=0, border_radius=3)
        enemy_shield_progress = round((self.opponent.shield / self.opponent.max_shield) * 100)
        enemy_shield_rect = pygame.Rect(settings.SCREEN_WIDTH - 3 - total_enemy_bar_width, enemy_image_rect.height + enemy_max_hp_rect.height + 9, enemy_shield_progress, 14)
        pygame.draw.rect(self.surface, "#0000FF", enemy_shield_rect, width=0, border_radius=3)
        enemy_shield_text = self.contestant_font.render(f"{self.opponent.shield} / {self.opponent.max_shield}", False, (230, 230, 230))
        text_rect = enemy_shield_text.get_rect()
        text_rect.center = enemy_max_shield_rect.center
        text_rect.y += 2
        self.surface.blit(enemy_shield_text, text_rect)
        enemy_text = self.contestant_font.render(f"{self.opponent.archetype.name.lower().title()}", False, (230, 230, 230))
        archetype_rect = enemy_text.get_rect()
        archetype_rect.midtop = (enemy_max_shield_rect.centerx, enemy_max_shield_rect.bottom + 4)
        self.surface.blit(enemy_text, archetype_rect)

    def render_draft(self):
        self.surface.fill((25, 25, 25))

        title = self.title_font.render("Choose a card", False, (230, 230, 230))
        self.surface.blit(title, title.get_rect(center=(settings.SCREEN_WIDTH // 2, 50)))

        btn_w, btn_h = 64, 24
        btn_x = settings.SCREEN_WIDTH // 2
        btn_y = settings.SCREEN_HEIGHT // 2 + 100

        self.draft_skip_rect = pygame.Rect(0, 0, btn_w, btn_h)
        self.draft_skip_rect.center = (btn_x, btn_y)

        if settings.DEBUG_MODE: pygame.draw.rect(self.surface, settings.DEBUG_COLORS.COLOR_4.value, self.draft_skip_rect, width=0)

        draft_skip_image = self.spritesheets["buttons"].get_image(96, 0, 32, 12)
        scaled_image = pygame.transform.scale(draft_skip_image, (btn_w, btn_h))
        self.surface.blit(scaled_image, self.draft_skip_rect)

        card_w, card_h = 84, 128
        total_w = 3 * card_w + 2 * 20
        start_x = (settings.SCREEN_WIDTH - total_w) // 2
        y_pos = settings.SCREEN_HEIGHT // 2 - card_h // 2

        self.draft_rects.clear()

        for i, card in enumerate(self.draft_options):
            x_pos = start_x + i * (card_w + 20)
            card_rect = pygame.Rect(x_pos, y_pos, card_w, card_h)
            self.draft_rects.append((card_rect, card))

            card_image = self.spritesheets["cards"].get_image(card.card_type["id"] % 10 * 42, card.card_type["id"] // 10 * 64, 42, 64)
            scaled_image = pygame.transform.scale(card_image, (card_w, card_h))
            self.surface.blit(scaled_image, (x_pos, y_pos))

            if card_rect.collidepoint(pygame.mouse.get_pos()):
                pygame.draw.rect(self.surface, (255, 255, 0), card_rect, width=2)

    def render_pause_overlay(self):
        overlay = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.surface.blit(overlay, (0, 0))

        title = self.title_font.render("Paused", False, (230, 230, 230))
        self.surface.blit(title, title.get_rect(center=(settings.SCREEN_WIDTH // 2, 50)))

        btn_w, btn_h = 64, 24
        btn_x = settings.SCREEN_WIDTH // 2
        btn_y = settings.SCREEN_HEIGHT // 2 + 30

        self.pause_button_rect = pygame.Rect(0, 0, btn_w, btn_h)
        self.pause_button_rect.center = (btn_x, btn_y)

        if settings.DEBUG_MODE: pygame.draw.rect(self.surface, settings.DEBUG_COLORS.COLOR_7.value, self.pause_button_rect, width=0)

        pause_button_image = self.spritesheets["buttons"].get_image(160, 0, 32, 12)
        scaled_image = pygame.transform.scale(pause_button_image, (btn_w, btn_h))
        self.surface.blit(scaled_image, self.pause_button_rect)

        btn_w, btn_h = 64, 24
        btn_x = settings.SCREEN_WIDTH // 2
        btn_y = settings.SCREEN_HEIGHT // 2 + 60

        self.pause_menu_button_rect = pygame.Rect(0, 0, btn_w, btn_h)
        self.pause_menu_button_rect.center = (btn_x, btn_y)

        if settings.DEBUG_MODE: pygame.draw.rect(self.surface, settings.DEBUG_COLORS.COLOR_7.value, self.pause_menu_button_rect, width=0)

        pause_menu_button_image = self.spritesheets["buttons"].get_image(192, 0, 32, 12)
        scaled_image = pygame.transform.scale(pause_menu_button_image, (btn_w, btn_h))
        self.surface.blit(scaled_image, self.pause_menu_button_rect)

    def render_game_over(self):
        self.surface.fill((25, 10, 10))

        title = self.title_font.render(f"You lost!", False, "#720707")
        text = self.font.render("On your journey...", False, (230, 230, 230))
        score_text = self.font.render(f"You've defeated {self.score} {"enemy" if self.score == 1 else "enemies"}", False, (230, 230, 230))
        self.surface.blit(title, title.get_rect(center=(settings.SCREEN_WIDTH // 2, 50)))
        self.surface.blit(text, text.get_rect(center=(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2 - 30)))
        self.surface.blit(score_text, score_text.get_rect(center=(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2 + 10)))

        btn_w, btn_h = 64, 24
        btn_x = settings.SCREEN_WIDTH // 2
        btn_y = settings.SCREEN_HEIGHT // 2 + 60

        self.game_over_button_rect = pygame.Rect(0, 0, btn_w, btn_h)
        self.game_over_button_rect.center = (btn_x, btn_y)

        if settings.DEBUG_MODE: pygame.draw.rect(self.surface, settings.DEBUG_COLORS.COLOR_1.value, self.game_over_button_rect, width=0)

        game_over_button_image = self.spritesheets["buttons"].get_image(128, 0, 32, 12)
        scaled_image = pygame.transform.scale(game_over_button_image, (btn_w, btn_h))
        self.surface.blit(scaled_image, self.game_over_button_rect)

    def setup_draft(self):
        self.draft_options.clear()

        pools = [
            settings.CardPools.COUTNDOWN_DEC.value,
            settings.CardPools.COUNTDOWN_INC.value,
            settings.CardPools.DAMAGE.value,
            settings.CardPools.HP.value,
            settings.CardPools.SHIELD.value,
        ]

        selected_pools = random.sample(pools, k=3)

        chosen_card_ids = []

        for pool in selected_pools:
            if random.random() < 0.000001: card_id = random.choice(settings.CardPools.SECRET.value)
            else: card_id = random.choice(pool)
            while card_id in chosen_card_ids: card_id = random.choice(pool)

            chosen_card_ids.append(card_id)
            self.draft_options.append(cards.Card(None, card_id, self))

    async def run(self):
        self.running = True
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11: self.toggle_fullscreen()

                if not self.in_transition:
                    if event.type == pygame.KEYDOWN:
                        if self.state == settings.GameState.MAINMENU.value:
                            if event.key == pygame.K_ESCAPE: self.running = False

                        elif self.state == settings.GameState.PLAYING.value:
                            if event.key == pygame.K_ESCAPE:
                                settings.get_sound("button_click.ogg").play()
                                self.state = settings.GameState.PAUSED.value

                        elif self.state == settings.GameState.PAUSED.value:
                            if event.key == pygame.K_ESCAPE:
                                settings.get_sound("archetype_select.ogg").play()
                                self.state = settings.GameState.PLAYING.value

                        elif self.state == settings.GameState.ARCHETYPECHOOSING.value:
                            if event.key == pygame.K_ESCAPE:
                                settings.get_sound("button_click.ogg").play()
                                self.trigger_transition(settings.GameState.MAINMENU.value)

                        elif self.state == settings.GameState.SETTINGSMENU.value:
                            if event.key == pygame.K_ESCAPE:
                                settings.get_sound("button_click.ogg").play()
                                self.state = settings.GameState.MAINMENU.value

                        elif self.state == settings.GameState.STATMENU.value:
                            if event.key == pygame.K_ESCAPE:
                                settings.get_sound("button_click.ogg").play()
                                self.state = settings.GameState.MAINMENU.value

                    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                        mouse_pos = event.pos

                        if self.state == settings.GameState.DRAFTING.value:                        
                            for rect, card in self.draft_rects:
                                if rect.collidepoint(mouse_pos):
                                    self.player.deck.append(card)
                                    settings.get_sound("draft_select.ogg").play()
                                    self.new_match()
                                    break

                            if self.draft_skip_rect.collidepoint(mouse_pos):
                                settings.get_sound("draft_select.ogg").play()
                                self.new_match()

                        elif self.state == settings.GameState.MAINMENU.value:
                            if self.menu_start_rect.collidepoint(mouse_pos):
                                settings.get_sound("button_click.ogg").play()
                                self.trigger_transition(settings.GameState.ARCHETYPECHOOSING.value)
                            elif self.settings_menu_rect.collidepoint(mouse_pos):
                                settings.get_sound("button_click.ogg").play()
                                self.state = settings.GameState.SETTINGSMENU.value
                            elif self.stat_menu_rect.collidepoint(mouse_pos):
                                settings.get_sound("button_click.ogg").play()
                                self.state = settings.GameState.STATMENU.value
                            if sys.platform != "emscripten":
                                if self.quit_rect.collidepoint(mouse_pos): self.running = False

                        elif self.state == settings.GameState.ARCHETYPECHOOSING.value:
                            for rect, archetype in self.archetype_menu_rects:
                                if rect.collidepoint(mouse_pos):
                                    settings.get_sound("archetype_select.ogg").play()
                                    self.new_game(archetype)
                            if self.back_rect.collidepoint(mouse_pos):
                                settings.get_sound("button_click.ogg").play()
                                self.trigger_transition(settings.GameState.MAINMENU.value)

                        elif self.state == settings.GameState.GAMEOVER.value:
                            if self.game_over_button_rect.collidepoint(mouse_pos):
                                settings.get_sound("archetype_select.ogg").play()
                                self.trigger_transition(settings.GameState.MAINMENU.value)

                        elif self.state == settings.GameState.PAUSED.value:
                            if self.pause_button_rect.collidepoint(mouse_pos):
                                settings.get_sound("archetype_select.ogg").play()
                                self.state = settings.GameState.PLAYING.value
                            elif self.pause_menu_button_rect.collidepoint(mouse_pos):
                                settings.get_sound("archetype_select.ogg").play()
                                if self.score > self.gamesave["highscore"]: self.gamesave["highscore"] = self.score
                                self.trigger_transition(settings.GameState.MAINMENU.value)

                        elif self.state == settings.GameState.SETTINGSMENU.value:
                            if self.back_rect.collidepoint(mouse_pos):
                                settings.get_sound("button_click.ogg").play()
                                self.state = settings.GameState.MAINMENU.value
                            elif self.fullscreen_rect.collidepoint(mouse_pos):
                                settings.get_sound("button_click.ogg").play()
                                self.toggle_fullscreen()
                            if sys.platform != "emscripten":
                                if self.wipe_data_rect.collidepoint(mouse_pos):
                                    settings.get_sound("lost.ogg").play()
                                    self.gamesave = settings.EMPTY_SAVE

                        elif self.state == settings.GameState.STATMENU.value:
                            if self.back_rect.collidepoint(mouse_pos):
                                settings.get_sound("button_click.ogg").play()
                                self.state = settings.GameState.MAINMENU.value
                            elif self.stat_hp_rect.collidepoint(mouse_pos):
                                settings.get_sound("menu_hover.ogg").play()
                                if self.gamesave["stat_points"] > 0:
                                    self.gamesave["stat_points"] -= 1
                                    self.gamesave["hp_stat"] += 1
                            elif self.stat_shield_rect.collidepoint(mouse_pos):
                                settings.get_sound("menu_hover.ogg").play()
                                if self.gamesave["stat_points"] > 0:
                                    self.gamesave["stat_points"] -= 1
                                    self.gamesave["shield_stat"] += 1

                        elif self.state == settings.GameState.PLAYING.value:
                            if self.pause_rect.collidepoint(mouse_pos):
                                settings.get_sound("button_click.ogg").play()
                                self.state = settings.GameState.PAUSED.value

                    if self.state == settings.GameState.PLAYING.value:
                        for obj in self.entities[:]: obj.handle_event(event, self)

            self.update()
            self.render()

            pygame.transform.scale(self.surface, self.screen.get_size(), self.screen)
            pygame.display.flip()

            self.delta_time = self.clock.tick(60) / 1000

            await asyncio.sleep(0)

        settings.save_game(self.gamesave)
        pygame.quit()