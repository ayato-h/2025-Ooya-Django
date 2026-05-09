from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from . import views

app_name = 'app'
urlpatterns = [
    path('',views.index_view, name='index'),
    path("setting/", views.setting_view, name="setting"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/edit/", views.profile_edit_view, name="profile_edit"),
    path("songs/", views.song_list_view, name="song-list"),
    path("songs/detail/", views.song_detail_view, name="song-detail"),
    path('favorite/', views.favorite_view, name='favorite'),
    path('favorite/<int:song_id>/', views.favorite_detail_view, name='favorite-detail'),
    path('favorite/<int:song_id>/save_lyrics/', views.save_lyrics, name='save_lyrics'),
    path('favorite/<int:song_id>/remove/', views.favorite_remove_view, name='favorite-remove'), 
    path('score/create/', views.ScoreLogCreateView.as_view(), name='create_score'), 
    path('score/list/', views.ScoreLogListView.as_view(), name='score_list'), 
    path('score/delete/<int:pk>/', views.ScoreLogDeleteView.as_view(), name='delete_score'),
    path('history/', views.HistoryListView.as_view(), name='history'),
    path('calc/', views.calc_view, name='calc'),
    path('quiz/', views.quiz_view, name='quiz'),
    path('sing_later/', views.sing_later_view, name='sing_later'),
    path("sing/<int:song_id>/later/", views.toggle_later, name="toggle-later"),
    path('unlock/', views.unlock_view, name='unlock'),
    path('friends/', views.friends_list_view, name='friends-list'),
    path('friends/request/<int:user_id>/', views.send_friend_request_view, name='friend-request'),
    path('friends/accept/<int:request_id>/', views.accept_friend_request_view, name='friend-accept'),
    path('friends/reject/<int:request_id>/', views.reject_friend_request_view, name='friend-reject'),
    path('friends/<int:friend_id>/profile/', views.friend_profile_view, name='friend-profile'),
    path('chat/<int:user_id>/', views.chat_with_user_view, name='chat-with-user'),
    path('chat/<int:room_id>/send/', views.send_message_view, name='send-message'),
    path('chat/message/delete/<int:message_id>/', views.delete_message_view, name='delete-message'),
    path('ranking/', views.ranking_view, name='ranking'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)