from django.contrib import admin
from django.urls import path, include
from . import views

app_name = 'visual'
urlpatterns = [
    path('',views.index_view, name='index'),
    path('contact/',views.contact_view, name='contact'),
    path('dice/',views.dice_view, name='dice'),
    path('gorilla/',views.gorilla_view, name='gorilla'),
    path('gorilla/result',views.gorilla_result_view, name='gorilla-result'),
    path('click-game/',views.click_game_view, name='click-game'),
    
]