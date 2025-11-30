from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PositionViewSet, user_positions

router = DefaultRouter()
router.register(r'', PositionViewSet, basename='position')

app_name = 'positions'

urlpatterns = [
    path('', include(router.urls)),
    path('user/', user_positions, name='user_positions'),
]

