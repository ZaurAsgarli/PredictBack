from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SecurityLogViewSet, LoginAttemptViewSet,
    security_logs_list, test_endpoint,
    admin_stats, admin_security, admin_suspicious_users, admin_ml_insights,
)

router = DefaultRouter()
router.register(r'logs', SecurityLogViewSet, basename='securitylog')
router.register(r'login-attempts', LoginAttemptViewSet, basename='loginattempt')

urlpatterns = [
    path('', include(router.urls)),
    path('security-logs/', security_logs_list, name='security-logs-list'),
    # Admin Dashboard API endpoints
    path('stats/', admin_stats, name='admin-stats'),
    path('security/', admin_security, name='admin-security'),
    path('suspicious/', admin_suspicious_users, name='admin-suspicious'),
    path('ml-insights/', admin_ml_insights, name='admin-ml-insights'),
]
