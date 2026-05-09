from django.contrib import admin
from django.urls import path, include
from . import views

app_name = 'casino'
urlpatterns = [
    path('',views.index_view, name='index'),
    path('baccara/',views.baccara_view, name='baccara'),
    path('baccara/bet/',views.baccara_bet_view, name='baccara-bet'),
    path('black_jack/',views.black_jack_view, name='black_jack'),
    path('black_jack/bet/',views.black_jack_bet_view, name='black_jack-bet'),
]