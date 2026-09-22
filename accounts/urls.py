from django.urls import path
from .views import login_view, refresh_token_view, profile_view

urlpatterns = [
    path('login/', login_view, name='login'),
    path('refresh/', refresh_token_view, name='refresh-token'),
    path('profile/', profile_view, name='profile'),
]