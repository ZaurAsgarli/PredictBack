from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from backend_api.api.users.models import User
from backend_api.api.trades.models import Trade
from django.db.models import Sum, Count, Avg, Q


def calculate_user_stats(user):
    """Calculate user stats from trades."""
    trades = Trade.objects.filter(user=user)
    total_trades = trades.count()
    
    if total_trades == 0:
        return {
            'total_predictions': 0,
            'win_rate': float(user.win_rate or 0),
            'current_streak': user.streak or 0,
        }
    
    # Count wins (completed trades where outcome matched prediction)
    wins = trades.filter(status='won').count()
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    return {
        'total_predictions': total_trades,
        'win_rate': round(win_rate, 2),
        'current_streak': user.streak or 0,
    }


@api_view(['GET'])
@permission_classes([AllowAny])
def global_leaderboard(request):
    """Global leaderboard - Top 100 users by total_points."""
    users = User.objects.order_by('-total_points')[:100]
    
    data = []
    for rank, user in enumerate(users, start=1):
        stats = calculate_user_stats(user)
        data.append({
            'rank': rank,
            'user_id': user.id,
            'username': user.username,
            'total_points': float(user.total_points or 0),
            'win_rate': stats['win_rate'] or float(user.win_rate or 0),
            'total_predictions': stats['total_predictions'],
            'current_streak': stats['current_streak'],
            'wallet_address': user.wallet_address,
        })
    
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def weekly_leaderboard(request):
    """Weekly leaderboard - users with most activity in the last 7 days."""
    week_ago = timezone.now() - timedelta(days=7)
    
    # Get users who made trades in the last week
    weekly_traders = Trade.objects.filter(
        created_at__gte=week_ago
    ).values('user').annotate(
        weekly_volume=Sum('amount_staked'),
        trade_count=Count('id')
    ).order_by('-weekly_volume')[:50]
    
    user_ids = [t['user'] for t in weekly_traders]
    users_map = {u.id: u for u in User.objects.filter(id__in=user_ids)}
    
    data = []
    for rank, trader in enumerate(weekly_traders, start=1):
        user = users_map.get(trader['user'])
        if user:
            data.append({
                'rank': rank,
                'user_id': user.id,
                'username': user.username,
                'total_points': float(user.total_points or 0),
                'weekly_volume': float(trader['weekly_volume'] or 0),
                'trade_count': trader['trade_count'],
                'win_rate': float(user.win_rate or 0),
                'wallet_address': user.wallet_address,
            })
    
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def monthly_leaderboard(request):
    """Monthly leaderboard - users with most activity in the last 30 days."""
    month_ago = timezone.now() - timedelta(days=30)
    
    # Get users who made trades in the last month
    monthly_traders = Trade.objects.filter(
        created_at__gte=month_ago
    ).values('user').annotate(
        monthly_volume=Sum('amount_staked'),
        trade_count=Count('id')
    ).order_by('-monthly_volume')[:50]
    
    user_ids = [t['user'] for t in monthly_traders]
    users_map = {u.id: u for u in User.objects.filter(id__in=user_ids)}
    
    data = []
    for rank, trader in enumerate(monthly_traders, start=1):
        user = users_map.get(trader['user'])
        if user:
            data.append({
                'rank': rank,
                'user_id': user.id,
                'username': user.username,
                'total_points': float(user.total_points or 0),
                'monthly_volume': float(trader['monthly_volume'] or 0),
                'trade_count': trader['trade_count'],
                'win_rate': float(user.win_rate or 0),
                'wallet_address': user.wallet_address,
            })
    
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def user_leaderboard(request, user_id):
    """Get specific user's rank and stats."""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    
    # Calculate rank
    rank = User.objects.filter(total_points__gt=user.total_points).count() + 1
    stats = calculate_user_stats(user)
    
    return Response({
        'rank': rank,
        'user_id': user.id,
        'username': user.username,
        'total_points': float(user.total_points or 0),
        'win_rate': stats['win_rate'],
        'total_predictions': stats['total_predictions'],
        'current_streak': stats['current_streak'],
        'wallet_address': user.wallet_address,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def test_endpoint(request):
    """
    Simple test endpoint for rate limiting tests.
    Returns a simple JSON response.
    """
    return Response({
        'message': 'Test endpoint working',
        'timestamp': timezone.now().isoformat()
    })
