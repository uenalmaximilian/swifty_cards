import settings
import random

class Model:
    def choose_card(self, hand, enemy, game): 
        pass

class Normal(Model):
    def choose_card(self, hand, enemy, game):
        best_play_card = None
        best_play_score = -99999.0

        best_dump_card = None
        best_dump_score = -99999.0

        player = game.player
        countdown = game.countdown

        for card in hand:
            c = card.card_type
            play_score = 0.0

            if c["dmg"] >= (player.hp + player.shield):
                play_score += 50000.0

            new_countdown = countdown + c["countd"]
            if new_countdown < 1.0:
                play_score += 50000.0
            if new_countdown < 0.5:
                play_score += 50000.0
            if new_countdown < 0.0:
                play_score += 100000.0

            enemy_hp_ratio = enemy.hp / enemy.max_hp if enemy.max_hp > 0 else 1.0
            missing_hp = enemy.max_hp - enemy.hp
            effective_heal = min(c["hp"], missing_hp) if c["hp"] > 0 else 0

            if c["shield"] > 0:
                if enemy.shield == 0:
                    play_score += 8000.0 + (c["shield"] * 2.0)
                else:
                    play_score += c["shield"] * (2.0 - enemy_hp_ratio) * 1.5

            if missing_hp > 0 and effective_heal > 0:
                heal_urgency = (1.0 - enemy_hp_ratio) * 10.0 + 1.0
                play_score += effective_heal * 3.0 * heal_urgency
            elif c["hp"] > 0 and effective_heal == 0:
                play_score -= 100.0

            if c["countd"] < 0:
                abs_time_change = abs(c["countd"])

                if countdown <= 5.0:
                    play_score -= 20000.0 
                elif new_countdown < 5.0:
                    play_score -= 10000.0
                else:
                    play_score += abs_time_change * 4.0

            elif c["countd"] > 0:
                if countdown < 5.0:
                    play_score += c["countd"] * 10.0 + 5000.0
                else:
                    play_score -= c["countd"] * 1.0

            player_hp_ratio = player.hp / player.max_hp if player.max_hp > 0 else 1.0
            play_score += c["dmg"] * (1.5 + (1.0 - player_hp_ratio))

            if play_score > best_play_score:
                best_play_score = play_score
                best_play_card = card

            dump_score = -10.0
            if c["hp"] > 0 and effective_heal == 0:
                dump_score += 50.0
            if c["countd"] > 0 and countdown >= 15.0:
                dump_score += 20.0

            if dump_score > best_dump_score:
                best_dump_score = dump_score
                best_dump_card = card

        if best_play_card and best_play_score > 0.0:
            return best_play_card, "play"

        if best_dump_card and best_dump_score > best_play_score:
            return best_dump_card, "dump"

        return (best_play_card if best_play_card else hand[0]), "play"

AI_REGISTRY = {
    settings.AITypes.NORMAL.value: Normal(),
}