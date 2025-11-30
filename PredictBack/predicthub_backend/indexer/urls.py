from django.urls import path
from .views import webhook_handler, rpc_endpoint

app_name = 'indexer'

urlpatterns = [
    path('', webhook_handler, name='webhook'),
    path('rpc/', rpc_endpoint, name='rpc'),
]

