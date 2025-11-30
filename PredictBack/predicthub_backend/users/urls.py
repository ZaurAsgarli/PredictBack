from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import SignUpView, login_view, me_view
from trades.views import user_trades
from positions.views import user_positions

app_name = 'users'

urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', login_view, name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', me_view, name='me'),
    path('me/trades/', user_trades, name='user_trades'),
    path('me/positions/', user_positions, name='user_positions'),
]

