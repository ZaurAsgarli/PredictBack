from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LiquidityEventViewSet

router = DefaultRouter()
router.register(r'', LiquidityEventViewSet, basename='liquidity-event')

app_name = 'liquidity'

urlpatterns = [
    path('', include(router.urls)),
]

