from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SecurityLogViewSet, LoginAttemptViewSet,
    security_logs_list, test_endpoint
)

router = DefaultRouter()
router.register(r'logs', SecurityLogViewSet, basename='securitylog')
router.register(r'login-attempts', LoginAttemptViewSet, basename='loginattempt')

urlpatterns = [
    path('', include(router.urls)),
    path('security-logs/', security_logs_list, name='security-logs-list'),
]

