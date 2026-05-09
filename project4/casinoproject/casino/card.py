import random

class Card:
    types = ['♡', '♤', '♢', '♧']
    numbers = ['A',2,3,4,5,6,7,8,9,10,'J','Q','K']
    
    def __init__(self, cards=None):
        if cards is None:
            self.create_cards()
        else:
            self.cards = cards

    def create_cards(self):
        self.cards = [f"{t}{n}" for t in Card.types for n in Card.numbers]

    def draw(self):
        if not self.cards:
            return None
        draw_card = random.choice(self.cards)
        self.cards.remove(draw_card)
        return draw_card

def card_score(card):
    num = card[1:]
    if num in ['J','Q','K','10']:
        return 0
    elif num == 'A':
        return 1
    else:
        return int(num)

def baccara_hand_score(hand):
    return sum(card_score(card) for card in hand) % 10

def draw_third_card(request, card):
    player_hand = request.session.get('player_cards')
    banker_hand = request.session.get('banker_cards')

    player_score = baccara_hand_score(player_hand)
    banker_score = baccara_hand_score(banker_hand)

    if player_score >= 8 or banker_score >= 8:
        return player_hand, banker_hand, player_score, banker_score

    if player_score <= 5:
        player_third = card.draw()
        player_hand.append(player_third)
        player_score = baccara_hand_score(player_hand)
    else:
        player_third = None

    banker_draw = False
    if player_third is None:
        if banker_score <= 5:
            banker_draw = True
    else:
        player_third_score = card_score(player_third)
        if banker_score <= 2:
            banker_draw = True
        elif banker_score == 3 and player_third_score != 8:
            banker_draw = True
        elif banker_score == 4 and 2 <= player_third_score <= 7:
            banker_draw = True
        elif banker_score == 5 and 4 <= player_third_score <= 7:
            banker_draw = True
        elif banker_score == 6 and player_third_score in [6, 7]:
            banker_draw = True

    if banker_draw:
        banker_third = card.draw()
        banker_hand.append(banker_third)
        banker_score = baccara_hand_score(banker_hand)

    request.session['player_cards'] = player_hand
    request.session['banker_cards'] = banker_hand

    return player_hand, banker_hand, player_score, banker_score

def black_jack_hand_score(hand):
    total = 0
    aces = 0

    if isinstance(hand, str):
        hand = [hand]

    for card in hand:
        if not card:
            continue

        score = card[1:]

        if score in ['J', 'Q', 'K', '10']:
            total += 10
        elif score == 'A':
            aces += 1
        else:
            if score.isdigit():
                total += int(score)
            else:
                continue

    for _ in range(aces):
        if total + 11 <= 21:
            total += 11
        else:
            total += 1

    return total

def blackjack_judge(player_cards, dealer_cards, back=True):
    player_score = black_jack_hand_score(player_cards)
    dealer_score = black_jack_hand_score(dealer_cards if back else dealer_cards)

    winner = None
    result = None

    # ブラックジャック判定（初回のみ）
    if len(player_cards) == 2 and player_score == 21:
        result = "ブラックジャック ▶︎ Player"
        winner = "player"
    elif len(dealer_cards) == 2 and dealer_score == 21 and not back:
        result = "ブラックジャック ▶︎ Dealer"
        winner = "dealer"

    # バースト判定（ゲーム終了扱いにはせず、結果表示用）
    if player_score > 21:
        result = "バースト ▶︎ Player"
    if dealer_score > 21 and not back:
        result = "バースト ▶︎ Dealer"

    # 両方のスコア比較（backがFalseのとき）
    if not back:
        if player_score > 21 and dealer_score > 21:
            result = "両者バースト"
            winner = "dealer"  # 通常ルールではディーラー勝ち扱い
        elif player_score > 21:
            result = "バースト勝ち ▶︎ Dealer"
            winner = "dealer"
        elif dealer_score > 21:
            result = "バースト勝ち ▶︎ Player"
            winner = "player"
        else:
            # 通常スコア比較
            if player_score > dealer_score:
                result = "勝者 ▶︎ Player"
                winner = "player"
            elif dealer_score > player_score:
                result = "勝者 ▶︎ Dealer"
                winner = "dealer"
            else:
                result = "引き分け"
                winner = "tie"
    else:
        # back=True の場合はまだ途中
        result = "▼次へ▼"

    return result, winner


def can_split(hand):
    if len(hand) != 2:
        return False

    def split_value(card):
        v = card[1:]
        if v in ['10', 'J', 'Q', 'K']:
            return 10
        return v

    return split_value(hand[0]) == split_value(hand[1])

def split_hand(card_obj, hand):
    hand1 = [hand[0], card_obj.draw()]
    hand2 = [hand[1], card_obj.draw()]
    return hand1, hand2

def hit_hand(card_obj, hand):
    hand.append(card_obj.draw())
    return hand

def is_bust(hand):
    return black_jack_hand_score(hand) > 21
