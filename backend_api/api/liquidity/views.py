from rest_framework import viewsets, permissions
from .models import LiquidityEvent
from .serializers import LiquidityEventSerializer


class LiquidityEventViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing liquidity events"""
    queryset = LiquidityEvent.objects.select_related('user', 'market').all()
    serializer_class = LiquidityEventSerializer
    permission_classes = [permissions.IsAuthenticated]

