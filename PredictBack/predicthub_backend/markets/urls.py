from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MarketViewSet, MarketCreateViewSet

router = DefaultRouter()
router.register(r'', MarketViewSet, basename='market')
router.register(r'create', MarketCreateViewSet, basename='market-create')

app_name = 'markets'

urlpatterns = [
    path('', include(router.urls)),
]

