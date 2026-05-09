from django.urls import path
from django.contrib.auth.views import LogoutView

from .views import signup_view, CustomLoginView

app_name = 'accounts'

urlpatterns = [
    path('signup/', signup_view, name='signup'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]