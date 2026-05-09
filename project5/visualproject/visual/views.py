from django.shortcuts import render
from django.utils import timezone
import random
import requests

def index_view(request):
    today = timezone.localdate()
    year = today.year

    url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/JP"
    response = requests.get(url)

    holidays = response.json()

    holiday_name = None

    for holiday in holidays:
        if holiday["date"] == str(today):
            holiday_name = holiday["localName"]
            break

    context = {
        "today": today,
        "holiday_name": holiday_name
    }

    return render(request, 'visual/index.html', context)

def contact_view(request):
    context = {
    }
    return render(request, 'visual/contact.html', context)

def dice_view(request):
    dice1 = random.randint(1,6)
    dice2 = random.randint(1,6)
    dice3 = random.randint(1,6)
    total = dice1 + dice2 + dice3

    context = {
        'dice1' : dice1,
        'dice2' : dice2,
        'dice3' : dice3,
        'total' : total,
    }
    return render(request, 'visual/dice.html', context)

def gorilla_view(request):
    items = ["normal"] * 6

    special_index = random.randint(0, 5)
    items[special_index] = "special"

    context = {
        "items": items
    }

    return render(request, 'visual/gorilla.html', context)

def gorilla_result_view(request):
    item = request.GET.get("item")  

    if item == "special":
        message = "あたり"
    else:
        message = "ハズレ"

    context = {
        'message' : message
    }

    return render(request, 'visual/gorilla-result.html', context)

def click_game_view(request):
    context = {
    }
    return render(request, 'visual/click-game.html', context)
