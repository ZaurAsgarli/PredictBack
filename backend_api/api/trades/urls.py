from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TradeViewSet, create_trade, user_trades

router = DefaultRouter()
router.register(r'', TradeViewSet, basename='trade')

app_name = 'trades'

urlpatterns = [
    path('', include(router.urls)),  # GET /trades/, POST /trades/, GET /trades/{id}/
    path('user/', user_trades, name='user_trades'),
]

