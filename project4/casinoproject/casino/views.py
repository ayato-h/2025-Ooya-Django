from django.shortcuts import render, redirect
from .card import Card, baccara_hand_score, draw_third_card, black_jack_hand_score, blackjack_judge, can_split, split_hand, hit_hand, is_bust
from accounts.models import CustomUser
from .models import BaccaratResult

def baccara_view(request):
    deck = request.session.get('deck')
    card = Card(deck)
    result = None
    bet = None
    bet_amount = None
    bet_target = None
    first_money = None

    user = request.user
    money = user.money

    player_cards = request.session.get('player_cards')
    banker_cards = request.session.get('banker_cards')

    if player_cards is None or banker_cards is None:
        player_cards = [card.draw(), card.draw()]
        banker_cards = [card.draw(), card.draw()]
        request.session['player_cards'] = player_cards
        request.session['banker_cards'] = banker_cards

    player_score = baccara_hand_score(player_cards)
    banker_score = baccara_hand_score(banker_cards)

    if request.method == "POST":
        if "bet" in request.POST:
            request.session['bet_amount'] = request.POST.get("bet_amount")
            request.session['bet_target'] = request.POST.get("bet")

            card = Card() 
            request.session['deck'] = card.cards

            player_cards = [card.draw(), card.draw()]
            banker_cards = [card.draw(), card.draw()]

            request.session['player_cards'] = player_cards
            request.session['banker_cards'] = banker_cards

        elif "draw" in request.POST:
            player_cards, banker_cards, player_score, banker_score = draw_third_card(request, card)
            request.session['player_cards'] = player_cards
            request.session['banker_cards'] = banker_cards

            if len(player_cards) >= 3 or len(banker_cards) >= 3:
                if player_score > banker_score:
                    result = "勝者 ▶︎ Player"
                elif banker_score > player_score:
                    result = "勝者 ▶︎ Banker"
                else:
                    result = "引き分け"

    player_score = baccara_hand_score(player_cards)
    banker_score = baccara_hand_score(banker_cards)

    if result is None:
        if player_score in (8, 9):
            if player_score == banker_score:
                result = "引き分け"
            else:
                result = "ナチュラル勝ち ▶︎ Player"
        elif banker_score in (8, 9):
            if player_score == banker_score:
                result = "引き分け"
            else:
                result = "ナチュラル勝ち ▶︎ Banker"
        else:
            result = "▼次へ▼"

    bet_amount = request.session.get('bet_amount')
    bet_target = request.session.get('bet_target')

    if result != "▼次へ▼" and bet_amount and bet_target:
        bet_amount = int(bet_amount)
        first_money = money
        change = 0  

        if "Player" in result:
            winner = "player"
        elif "Banker" in result:
            winner = "banker"
        else:
            winner = "tie"

        BaccaratResult.objects.create(result=winner)


        if bet_target == winner:
            if winner == "player":
                change = bet_amount

            elif winner == "banker":
                fee = (bet_amount * 5) // 100
                change = bet_amount - fee

            elif winner == "tie":
                change = bet_amount * 8
        else:
            change = -bet_amount

        money += change

        bet = f"+{change}" if change > 0 else f"{change}"

        user.money = money
        user.save()

    can_draw = (
        result == "▼次へ▼"
        and player_score < 8
        and banker_score < 8
    )

    context = {
        'player_cards': player_cards,
        'banker_cards': banker_cards,
        'player_score': player_score,
        'banker_score': banker_score,
        'result': result,
        'can_draw' : can_draw,
        'bet' : bet,
        'money' : money,
        'first_money' : first_money
    }

    return render(request, 'casino/baccara.html', context)

def baccara_bet_view(request):
    user = request.user
    money = user.money
    results = BaccaratResult.objects.order_by('created_at')  

    columns = []
    if results:
        current_col = []
        prev_result = None

        for r in results:
            if prev_result is None:
                current_col.append(r)
            else:
                if r.result == 'tie':
                    current_col.append(r)
                elif r.result == prev_result:
                    current_col.append(r)
                else:
                    columns.append(current_col)
                    current_col = [r]
            if r.result != 'tie':
                prev_result = r.result

        if current_col:
            columns.append(current_col)


    max_height = max(len(col) for col in columns) if columns else 0
    table = []
    for row_idx in range(max_height):
        row = []
        for col in columns:
            if row_idx < len(col):
                if col[row_idx].result == 'player':
                    row.append('⚫︎')
                elif col[row_idx].result == 'banker':
                    row.append('✖︎')
                else:
                    row.append('△')
            else:
                row.append('') 
        table.append(row)

    context = {
        'money': money,
        'table': table,  
    }
    return render(request, 'casino/baccara_bet.html', context)
# player_cards = ['♡A','♡A']

def black_jack_view(request):
    card = Card(request.session.get('deck'))

    user = request.user
    money = user.money
    first_money = money

    player_cards = request.session.get('player_cards', [])
    player_split_cards = request.session.get('player_split_cards', [])
    dealer_cards = request.session.get('dealer_cards', [])
    split = request.session.get('split', False)

    back = True
    result = None
    split_result = None
    bet = None

    if not player_cards or not dealer_cards:
        player_cards = [card.draw(), card.draw()]
        dealer_cards = [card.draw(), card.draw()]
        player_split_cards = []
        split = False
        request.session['player_cards'] = player_cards
        request.session['dealer_cards'] = dealer_cards
        request.session['player_split_cards'] = player_split_cards
        request.session['split'] = split

    if request.method == "POST":
        if "bet" in request.POST:
            bet_amount = int(request.POST.get("bet_amount", 0))
            bet_target = request.POST.get("bet")
            request.session['bet_amount'] = bet_amount
            request.session['bet_target'] = bet_target

            card = Card()
            request.session['deck'] = card.cards

            # player_cards = [card.draw(), card.draw()]
            player_cards = ['♡A','♡A']
            dealer_cards = [card.draw(), card.draw()]
            player_split_cards = []
            split = False

            request.session['player_cards'] = player_cards
            request.session['dealer_cards'] = dealer_cards
            request.session['player_split_cards'] = player_split_cards
            request.session['split'] = split

        elif "hit" in request.POST:
            target = request.POST.get("hit")
            if target == "split" and player_split_cards:
                player_split_cards.append(card.draw())
                request.session['player_split_cards'] = player_split_cards
            else:
                player_cards.append(card.draw())
                request.session['player_cards'] = player_cards


        elif "stand" in request.POST:
            back = False
            dealer_score = black_jack_hand_score(dealer_cards)
            while dealer_score < 17:
                dealer_cards.append(card.draw())
                dealer_score = black_jack_hand_score(dealer_cards)
            request.session['dealer_cards'] = dealer_cards

        elif "split" in request.POST:
            if not split and len(player_cards) == 2 and player_cards[0][1:] == player_cards[1][1:]:
                split = True
                player_split_cards = [player_cards.pop()]
                request.session['player_cards'] = player_cards
                request.session['player_split_cards'] = player_split_cards
                request.session['split'] = split

    player_score = black_jack_hand_score(player_cards)
    split_score = black_jack_hand_score(player_split_cards) if player_split_cards else 0
    dealer_score = black_jack_hand_score([dealer_cards[0]]) if back else black_jack_hand_score(dealer_cards)

    main_result, main_winner = blackjack_judge(player_cards, dealer_cards, back)
    split_result, split_winner = (None, None)
    if player_split_cards:
        split_result, split_winner = blackjack_judge(player_split_cards, dealer_cards, back)

    bet_amount = request.session.get('bet_amount', 0)
    bet_target = request.session.get('bet_target')
    if not back and bet_amount > 0 and bet_target:
        total_change = 0

        if bet_target == main_winner:
            if main_winner == "player":
                total_change += bet_amount
            elif main_winner == "dealer":
                fee = (bet_amount * 5) // 100
                total_change += bet_amount - fee
        else:
            total_change -= bet_amount

        if player_split_cards:
            if bet_target == split_winner:
                if split_winner == "player":
                    total_change += bet_amount
                elif split_winner == "dealer":
                    fee = (bet_amount * 5) // 100
                    total_change += bet_amount - fee
            else:
                total_change -= bet_amount

        money += total_change
        bet = f"+{total_change}" if total_change > 0 else f"{total_change}"
        user.money = money
        user.save()

        request.session['bet_amount'] = 0
        request.session['bet_target'] = None

    can_split_flag = False
    if not split and len(player_cards) == 2 and player_cards[0][1:] == player_cards[1][1:] and back:
        can_split_flag = True

    can_draw = back and player_score < 21

    context = {
        'player_cards': player_cards,
        'player_split_cards': player_split_cards,
        'player_score': player_score,
        'split_score': split_score,
        'dealer_cards': dealer_cards,
        'dealer_score': dealer_score,
        'back': back,
        'split': split,
        'result': main_result,
        'split_result': split_result,
        'bet': bet,
        'can_draw': can_draw,
        'can_split': can_split_flag,
        'money': money,
        'first_money': first_money,
    }

    return render(request, 'casino/black_jack.html', context)


def black_jack_bet_view(request):
    user = request.user
    money = user.money
    context = {
        'money' : money
    }
    return render(request, 'casino/black_jack_bet.html', context)

def index_view(request):
    return render(request, 'casino/index.html')
