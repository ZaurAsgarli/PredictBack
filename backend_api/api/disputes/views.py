from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers
from django.utils import timezone
from .models import Dispute
from .serializers import DisputeSerializer
from backend_api.api.markets.models import Market, Resolution


class DisputeViewSet(viewsets.ModelViewSet):
    """ViewSet for dispute operations"""
    queryset = Dispute.objects.select_related('user', 'market').all()
    serializer_class = DisputeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Handle Swagger schema generation (when user is anonymous)
        if getattr(self, 'swagger_fake_view', False) or not self.request.user.is_authenticated:
            return Dispute.objects.none()
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        return queryset
    
    def perform_create(self, serializer):
        market = serializer.validated_data['market']
        
        # Check if market is resolved
        if market.status != 'resolved':
            raise serializers.ValidationError("Can only dispute resolved markets")
        
        # Check if dispute window is still open
        try:
            resolution = market.resolution
            if timezone.now() > resolution.dispute_window:
                raise serializers.ValidationError("Dispute window has closed")
        except Resolution.DoesNotExist:
            raise serializers.ValidationError("Market resolution not found")
        
        # Check if user already disputed
        if Dispute.objects.filter(user=self.request.user, market=market).exists():
            raise serializers.ValidationError("You have already disputed this market")
        
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def accept(self, request, pk=None):
        """Accept a dispute (admin only)"""
        dispute = self.get_object()
        dispute.status = 'accepted'
        dispute.resolved_at = timezone.now()
        dispute.save()
        
        # Revert market resolution (would trigger additional logic in production)
        market = dispute.market
        market.status = 'active'
        market.resolution_outcome = None
        market.save()
        
        return Response({'status': 'Dispute accepted'})
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        """Reject a dispute (admin only)"""
        dispute = self.get_object()
        dispute.status = 'rejected'
        dispute.resolved_at = timezone.now()
        dispute.save()
        return Response({'status': 'Dispute rejected'})

