from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


# Placeholder views - implement leaderboard functionality as needed
@api_view(['GET'])
@permission_classes([AllowAny])
def global_leaderboard(request):
    return Response({'message': 'Global leaderboard - not implemented yet'})


@api_view(['GET'])
@permission_classes([AllowAny])
def weekly_leaderboard(request):
    return Response({'message': 'Weekly leaderboard - not implemented yet'})


@api_view(['GET'])
@permission_classes([AllowAny])
def monthly_leaderboard(request):
    return Response({'message': 'Monthly leaderboard - not implemented yet'})


@api_view(['GET'])
@permission_classes([AllowAny])
def user_leaderboard(request, user_id):
    return Response({'message': f'User {user_id} leaderboard - not implemented yet'})


@api_view(['GET'])
@permission_classes([AllowAny])
def test_endpoint(request):
    """
    Simple test endpoint for rate limiting tests.
    Returns a simple JSON response.
    """
    from django.utils import timezone
    return Response({
        'message': 'Test endpoint working',
        'timestamp': timezone.now().isoformat()
    })
