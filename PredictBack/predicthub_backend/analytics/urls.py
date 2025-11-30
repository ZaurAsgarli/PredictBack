from django.urls import path
from .views import global_leaderboard, weekly_leaderboard, monthly_leaderboard, user_leaderboard

app_name = 'analytics'

urlpatterns = [
    path('global/', global_leaderboard, name='global_leaderboard'),
    path('weekly/', weekly_leaderboard, name='weekly_leaderboard'),
    path('monthly/', monthly_leaderboard, name='monthly_leaderboard'),
    path('user/<int:user_id>/', user_leaderboard, name='user_leaderboard'),
]

