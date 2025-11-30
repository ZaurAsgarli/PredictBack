from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import Position
from .serializers import PositionSerializer


class PositionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing positions"""
    queryset = Position.objects.select_related('user', 'market').all()
    serializer_class = PositionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Handle Swagger schema generation (when user is anonymous)
        if getattr(self, 'swagger_fake_view', False) or not self.request.user.is_authenticated:
            return Position.objects.none()
        return super().get_queryset().filter(user=self.request.user)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_positions(request):
    """Get current user's positions"""
    positions = Position.objects.filter(user=request.user).order_by('-updated_at')
    
    from rest_framework.pagination import PageNumberPagination
    paginator = PageNumberPagination()
    page = paginator.paginate_queryset(positions, request)
    serializer = PositionSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)

