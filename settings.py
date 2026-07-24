import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
from enum import Enum
import sys
import json
from cryptography.fernet import Fernet
from pathlib import Path
from platformdirs import user_data_dir

GAME_NAME = "SwiftyCards"
DEV_NAME = "Apteryx"
SAVE_DIR = Path(user_data_dir(GAME_NAME, DEV_NAME))
SAVE_FILE_PATH = SAVE_DIR / "savegame.dat"
EMPTY_SAVE = {
                "gold": 0,
                "stat_points": 0,
                "hp_stat": 0,
                "shield_stat": 0
            }

SCREEN_WIDTH = 480
SCREEN_HEIGHT = 270
DEBUG_MODE = 0
SPRITESHEET_FILTER_COLOR = "#007F00"
MAX_CARD_ID = 15
KEY = b"v4YVv0PdJehS6eypHJ1PXPvvOTJtdlkdRcJzZUl6vEg="

class Directories(Enum):
    ASSETS = "assets"
    IMAGES = "images"
    SOUNDS = "sounds"

class DEBUG_COLORS(Enum):
    COLOR_0 = "#000000"
    COLOR_1 = "#FF0000"
    COLOR_2 = "#00FF00"
    COLOR_3 = "#0000FF"
    COLOR_4 = "#FFFF00"
    COLOR_5 = "#FF00FF"
    COLOR_6 = "#00FFFF"
    COLOR_7 = "#FFFFFF"

class Turns(Enum):
    PLAYER = 1
    ENEMY = 2

class CardTypes(Enum):
    NONE            = {"id": 0, "countd": 0, "dmg": 0, "hp": 0, "shield": 0}
    COUNTDOWN_DEC_1 = {"id": 1, "countd": -1, "dmg": 0, "hp": 0, "shield": 0}
    COUNTDOWN_DEC_2 = {"id": 2, "countd": -3, "dmg": 0, "hp": 0, "shield": 0}
    COUNTDOWN_DEC_3 = {"id": 3, "countd": -5, "dmg": 0, "hp": 0, "shield": 0}
    COUNTDOWN_INC_1 = {"id": 4, "countd": 1, "dmg": 0, "hp": 0, "shield": 0}
    COUNTDOWN_INC_2 = {"id": 5, "countd": 3, "dmg": 0, "hp": 0, "shield": 0}
    COUNTDOWN_INC_3 = {"id": 6, "countd": 5, "dmg": 0, "hp": 0, "shield": 0}
    DMG_1           = {"id": 7, "countd": 0, "dmg": 2, "hp": 0, "shield": 0}
    DMG_2           = {"id": 8, "countd": 0, "dmg": 5, "hp": 0, "shield": 0}
    DMG_3           = {"id": 9, "countd": 0, "dmg": 8, "hp": 0, "shield": 0}
    HP_1            = {"id": 10, "countd": 0, "dmg": 0, "hp": 3, "shield": 0}
    HP_2            = {"id": 11, "countd": 0, "dmg": 0, "hp": 5, "shield": 0}
    HP_3            = {"id": 12, "countd": 0, "dmg": 0, "hp": 7, "shield": 0}
    SHIELD_1        = {"id": 13, "countd": 0, "dmg": 0, "hp": 0, "shield": 1}
    SHIELD_2        = {"id": 14, "countd": 0, "dmg": 0, "hp": 0, "shield": 2}
    SHIELD_3        = {"id": 15, "countd": 0, "dmg": 0, "hp": 0, "shield": 4}
    TETO            = {"id": 99, "countd": 100, "dmg": 100, "hp": 100, "shield": 100}

    @classmethod
    def get_by_id(self, card_id):
        for member in self:
            if member.value["id"] == card_id:
                return member.value
        return self.NONE.value

class CardPools(Enum):
    START_COUTNDOWN_DEC = [1, 2, 3]
    START_COUNTDOWN_INC = [4, 5, 6]
    START_DAMAGE = [7, 8, 9]
    START_HP = [10, 11, 12]
    START_SHIELD = [13, 14, 15]
    COUTNDOWN_DEC = [1, 2, 3]
    COUNTDOWN_INC = [4, 5, 6]
    DAMAGE = [7, 8, 9]
    HP = [10, 11, 12]
    SHIELD = [13, 14, 15]
    SECRET = [99]

class AITypes(Enum):
    NORMAL = 0

class GameState(Enum):
    MAINMENU = 0
    PAUSED = 1
    PLAYING = 2
    DRAFTING = 3
    GAMEOVER = 4
    ARCHETYPECHOOSING = 5
    SETTINGSMENU = 6
    STATMENU = 7

class TransitionStep(Enum):
    FREEZE = 0
    FADEOUT = 1
    FADEIN = 2
    HOLD = 3

class Archetype(Enum):
    BALANCED = 0
    AGGRESSIVE = 1
    DEFENSIVE = 2
    UTILITY = 3

class Decks(Enum):
    BALANCED = {
        "deck": [
        CardTypes.DMG_1.value, CardTypes.DMG_1.value,
        CardTypes.HP_1.value, CardTypes.HP_1.value,
        CardTypes.SHIELD_2.value,
        CardTypes.COUNTDOWN_DEC_1.value, CardTypes.COUNTDOWN_INC_1.value
        ],
        "hp": 10,
        "shield": 5
    }
    AGGRESSIVE = {
        "deck": [
            CardTypes.DMG_1.value, CardTypes.DMG_1.value, CardTypes.DMG_2.value,
            CardTypes.COUNTDOWN_DEC_1.value, CardTypes.COUNTDOWN_DEC_2.value, CardTypes.COUNTDOWN_INC_1.value,
            CardTypes.SHIELD_1.value
        ],
        "hp": 8,
        "shield": 6
    }
    DEFENSIVE = {
        "deck": [
            CardTypes.HP_1.value, CardTypes.HP_2.value,
            CardTypes.SHIELD_2.value, CardTypes.SHIELD_2.value,
            CardTypes.COUNTDOWN_INC_2.value, CardTypes.COUNTDOWN_DEC_1.value,
            CardTypes.DMG_1.value
        ],
        "hp": 12,
        "shield": 8
    }
    UTILITY = {
        "deck": [
            CardTypes.COUNTDOWN_INC_2.value, CardTypes.COUNTDOWN_INC_2.value,
            CardTypes.COUNTDOWN_DEC_2.value, CardTypes.COUNTDOWN_DEC_1.value,
            CardTypes.HP_1.value, CardTypes.SHIELD_1.value,
            CardTypes.DMG_1.value
        ],
        "hp": 15,
        "shield": 3
    }

class DeckStrings(Enum):
    BALANCED = "2x -2 DMG\n2x +3 HP\n1x +1 Shield\n1x -1 Countdown\n1x +1 Countdown"
    AGGRESSIVE = "2x -2 DMG\n1x -5 DMG\n1x -1 Countdown\n1x -3 Countdown\n1x +1 Countdown\n1x +1 Shield"
    DEFENSIVE = "1x +3 HP\n1x +5 HP\n2x +2 Shield\n1x +3 Countdown\n1x -1 Countdown\n1x -2 DMG"
    UTILITY = "2x +3 Countdown\n2x -3 Countdown\n1x +3 HP\n1x +1 Shield\n1x -2 DMG"

def get_image(name: str):
    if hasattr(sys, "_MEIPASS"): base_path = sys._MEIPASS
    else: base_path = os.path.abspath(".")
    asset_path = os.path.join(base_path, Directories.ASSETS.value, Directories.IMAGES.value, name)
    return pygame.image.load(asset_path).convert_alpha()

def get_sound(name: str):
    if hasattr(sys, "_MEIPASS"): base_path = sys._MEIPASS
    else: base_path = os.path.abspath(".")
    asset_path = os.path.join(base_path, Directories.ASSETS.value, Directories.SOUNDS.value, name)
    return pygame.mixer.Sound(asset_path)

def ensure_directory():
    SAVE_DIR.mkdir(parents=True, exist_ok=True)

def load_game():
    if not SAVE_FILE_PATH.exists():
        return EMPTY_SAVE

    try:
        with open(SAVE_FILE_PATH, "rb") as f:
            encrypted = f.read()
        decrypted = Fernet(KEY).decrypt(encrypted)
        data = json.loads(decrypted.decode("utf-8"))
        return data
    except Exception:
        return EMPTY_SAVE

def save_game(data: dict):
    try:
        ensure_directory()
        bytedata = json.dumps(data).encode("utf-8")
        encrypted = Fernet(KEY).encrypt(bytedata)
        with open(SAVE_FILE_PATH, "wb") as f:
            f.write(encrypted)
    except Exception: pass