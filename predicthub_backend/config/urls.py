"""
URL configuration for predicthub_backend project.
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from strawberry.django.views import GraphQLView
from .graphql_schema import schema
from indexer.views import OnchainWebhookView
from webhooks.onchain_webhook import onchain_webhook
from indexer.admin import recent_events_view, backfill_status_view, heartbeat_view


def api_root(request):
    """Root API endpoint with API information"""
    return JsonResponse({
        'name': 'PredictHub API',
        'version': '1.0.0',
        'description': 'Community Prediction Market Backend API',
        'endpoints': {
            'authentication': '/api/users/',
            'markets': '/api/markets/',
            'trades': '/api/trades/',
            'positions': '/api/positions/',
            'liquidity': '/api/liquidity/',
            'indexer': '/api/indexer/',
            'disputes': '/api/disputes/',
            'leaderboard': '/api/analytics/',
            'admin': '/admin/',
            'api_docs': '/swagger/',
            'graphql': '/graphql/',
        },
        'documentation': {
            'swagger': '/swagger/',
            'redoc': '/redoc/',
        }
    })

schema_view = get_schema_view(
    openapi.Info(
        title="PredictHub API",
        default_version='v1',
        description="Community Prediction Market Backend API",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@predicthub.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Root endpoint
    path('', api_root, name='api-root'),
    
    # Admin
    path('admin/', admin.site.urls),
    # Indexer monitoring views
    path('admin/indexer/recent-events/', admin.site.admin_view(recent_events_view), name='indexer_recent_events'),
    path('admin/indexer/backfill-status/', admin.site.admin_view(backfill_status_view), name='indexer_backfill_status'),
    path('admin/indexer/heartbeat/', admin.site.admin_view(heartbeat_view), name='indexer_heartbeat'),
    
    # API Documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    
    # GraphQL
    path('graphql/', GraphQLView.as_view(schema=schema)),
    
    # API Routes - All under /api/ prefix
    path('api/users/', include('users.urls'), name='users'),
    path('api/markets/', include('markets.urls'), name='markets'),
    path('api/trades/', include('trades.urls'), name='trades'),
    path('api/positions/', include('positions.urls'), name='positions'),
    path('api/liquidity/', include('liquidity.urls'), name='liquidity'),
    path('api/indexer/', include('indexer.urls'), name='indexer'),
    path('api/disputes/', include('disputes.urls'), name='disputes'),
    path('api/analytics/', include('analytics.urls'), name='analytics'),
    
    # Webhooks (legacy support, can be moved to /api/indexer/ if needed)
    path('api/webhook/onchain/', OnchainWebhookView.as_view(), name='onchain-webhook'),
    path('webhooks/onchain/', onchain_webhook, name='onchain-webhook-new'),
]

