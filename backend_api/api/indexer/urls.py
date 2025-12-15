from django.urls import path
from .views import OnchainWebhookView
from .rpc_server import jsonrpc_endpoint

app_name = 'indexer'

urlpatterns = [
    path('webhook/', OnchainWebhookView.as_view(), name='onchain-webhook'),
    path('rpc/', jsonrpc_endpoint, name='jsonrpc-endpoint'),
]

