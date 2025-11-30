from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import Coalesce
from decimal import Decimal
from datetime import timedelta
from users.models import User
from positions.models import Position
from trades.models import Trade
from markets.models import OutcomeToken
from positions.services import PositionService


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def global_leaderboard(request):
    """
    Get global leaderboard ranked by total PnL.
    
    Returns top 100 users with:
    - user id
    - username
    - total_pnl = sum(position_size * (current_price - entry_price))
    - total_volume = sum(trades.amount_staked)
    """
    # Get all users with their positions and trades
    users = User.objects.prefetch_related(
        'positions__market__outcome_tokens',
        'trades'
    ).all()
    
    leaderboard_data = []
    
    # Prefetch all positions and outcome tokens to avoid N+1 queries
    all_positions = Position.objects.select_related('market', 'user').all()
    positions_by_user = {}
    all_markets = set()
    
    for position in all_positions:
        if position.user_id not in positions_by_user:
            positions_by_user[position.user_id] = []
        positions_by_user[position.user_id].append(position)
        all_markets.add(position.market_id)
    
    # Fetch all outcome tokens in one query
    outcome_tokens = OutcomeToken.objects.filter(market_id__in=all_markets).select_related('market')
    tokens_by_market = {}
    for token in outcome_tokens:
        if token.market_id not in tokens_by_market:
            tokens_by_market[token.market_id] = {}
        tokens_by_market[token.market_id][token.outcome_type] = token
    
    # Prefetch all trade volumes in one query
    trade_volumes = Trade.objects.values('user_id').annotate(
        total_volume=Coalesce(Sum('amount_staked'), Decimal('0'))
    )
    volumes_by_user = {item['user_id']: item['total_volume'] for item in trade_volumes}
    
    for user in users:
        # Calculate total PnL across all positions
        total_pnl = Decimal('0')
        positions = positions_by_user.get(user.id, [])
        
        for position in positions:
            if position.yes_tokens == 0 and position.no_tokens == 0:
                continue
            
            # Get current prices from prefetched data
            market_tokens = tokens_by_market.get(position.market_id, {})
            yes_token = market_tokens.get('YES')
            no_token = market_tokens.get('NO')
            
            current_yes_price = yes_token.price if yes_token else Decimal('0.5')
            current_no_price = no_token.price if no_token else Decimal('0.5')
            
            # Calculate average entry prices
            entry_yes_price = PositionService.get_average_entry_price(position, 'YES')
            entry_no_price = PositionService.get_average_entry_price(position, 'NO')
            
            # Calculate PnL for YES tokens
            if position.yes_tokens > 0 and entry_yes_price > 0:
                yes_pnl = position.yes_tokens * (current_yes_price - entry_yes_price)
                total_pnl += yes_pnl
            
            # Calculate PnL for NO tokens
            if position.no_tokens > 0 and entry_no_price > 0:
                no_pnl = position.no_tokens * (current_no_price - entry_no_price)
                total_pnl += no_pnl
        
        # Get total volume from prefetched data
        total_volume = volumes_by_user.get(user.id, Decimal('0'))
        
        leaderboard_data.append({
            'user_id': user.id,
            'username': user.username,
            'total_pnl': float(total_pnl),
            'total_volume': float(total_volume),
        })
    
    # Sort by total_pnl descending and get top 100
    leaderboard_data.sort(key=lambda x: x['total_pnl'], reverse=True)
    leaderboard_data = leaderboard_data[:100]
    
    # Add rank
    for idx, entry in enumerate(leaderboard_data, start=1):
        entry['rank'] = idx
    
    return Response(leaderboard_data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def weekly_leaderboard(request):
    """
    Get weekly leaderboard ranked by total PnL (last 7 days).
    """
    week_ago = timezone.now() - timedelta(days=7)
    
    # Get users who have trades in the last week
    users_with_recent_trades = User.objects.filter(
        trades__created_at__gte=week_ago
    ).distinct().prefetch_related(
        'positions__market__outcome_tokens',
        'trades'
    )
    
    # Prefetch outcome tokens for all markets
    all_markets = set()
    for user in users_with_recent_trades:
        positions = Position.objects.filter(user=user).select_related('market')
        for position in positions:
            all_markets.add(position.market_id)
    
    outcome_tokens = OutcomeToken.objects.filter(market_id__in=all_markets).select_related('market')
    tokens_by_market = {}
    for token in outcome_tokens:
        if token.market_id not in tokens_by_market:
            tokens_by_market[token.market_id] = {}
        tokens_by_market[token.market_id][token.outcome_type] = token
    
    leaderboard_data = []
    
    for user in users_with_recent_trades:
        # Calculate total PnL (same as global)
        total_pnl = Decimal('0')
        positions = Position.objects.filter(user=user).select_related('market')
        
        for position in positions:
            if position.yes_tokens == 0 and position.no_tokens == 0:
                continue
            
            # Get current prices from prefetched data
            market_tokens = tokens_by_market.get(position.market_id, {})
            yes_token = market_tokens.get('YES')
            no_token = market_tokens.get('NO')
            
            current_yes_price = yes_token.price if yes_token else Decimal('0.5')
            current_no_price = no_token.price if no_token else Decimal('0.5')
            
            entry_yes_price = PositionService.get_average_entry_price(position, 'YES')
            entry_no_price = PositionService.get_average_entry_price(position, 'NO')
            
            if position.yes_tokens > 0 and entry_yes_price > 0:
                yes_pnl = position.yes_tokens * (current_yes_price - entry_yes_price)
                total_pnl += yes_pnl
            
            if position.no_tokens > 0 and entry_no_price > 0:
                no_pnl = position.no_tokens * (current_no_price - entry_no_price)
                total_pnl += no_pnl
        
        # Calculate total volume for the week
        total_volume = Trade.objects.filter(
            user=user,
            created_at__gte=week_ago
        ).aggregate(
            total=Coalesce(Sum('amount_staked'), Decimal('0'))
        )['total'] or Decimal('0')
        
        leaderboard_data.append({
            'user_id': user.id,
            'username': user.username,
            'total_pnl': float(total_pnl),
            'total_volume': float(total_volume),
        })
    
    # Sort by total_pnl descending and get top 100
    leaderboard_data.sort(key=lambda x: x['total_pnl'], reverse=True)
    leaderboard_data = leaderboard_data[:100]
    
    # Add rank
    for idx, entry in enumerate(leaderboard_data, start=1):
        entry['rank'] = idx
    
    return Response(leaderboard_data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def monthly_leaderboard(request):
    """
    Get monthly leaderboard ranked by total PnL (last 30 days).
    """
    month_ago = timezone.now() - timedelta(days=30)
    
    # Get users who have trades in the last month
    users_with_recent_trades = User.objects.filter(
        trades__created_at__gte=month_ago
    ).distinct().prefetch_related(
        'positions__market__outcome_tokens',
        'trades'
    )
    
    # Prefetch outcome tokens for all markets
    all_markets = set()
    for user in users_with_recent_trades:
        positions = Position.objects.filter(user=user).select_related('market')
        for position in positions:
            all_markets.add(position.market_id)
    
    outcome_tokens = OutcomeToken.objects.filter(market_id__in=all_markets).select_related('market')
    tokens_by_market = {}
    for token in outcome_tokens:
        if token.market_id not in tokens_by_market:
            tokens_by_market[token.market_id] = {}
        tokens_by_market[token.market_id][token.outcome_type] = token
    
    leaderboard_data = []
    
    for user in users_with_recent_trades:
        # Calculate total PnL (same as global)
        total_pnl = Decimal('0')
        positions = Position.objects.filter(user=user).select_related('market')
        
        for position in positions:
            if position.yes_tokens == 0 and position.no_tokens == 0:
                continue
            
            # Get current prices from prefetched data
            market_tokens = tokens_by_market.get(position.market_id, {})
            yes_token = market_tokens.get('YES')
            no_token = market_tokens.get('NO')
            
            current_yes_price = yes_token.price if yes_token else Decimal('0.5')
            current_no_price = no_token.price if no_token else Decimal('0.5')
            
            entry_yes_price = PositionService.get_average_entry_price(position, 'YES')
            entry_no_price = PositionService.get_average_entry_price(position, 'NO')
            
            if position.yes_tokens > 0 and entry_yes_price > 0:
                yes_pnl = position.yes_tokens * (current_yes_price - entry_yes_price)
                total_pnl += yes_pnl
            
            if position.no_tokens > 0 and entry_no_price > 0:
                no_pnl = position.no_tokens * (current_no_price - entry_no_price)
                total_pnl += no_pnl
        
        # Calculate total volume for the month
        total_volume = Trade.objects.filter(
            user=user,
            created_at__gte=month_ago
        ).aggregate(
            total=Coalesce(Sum('amount_staked'), Decimal('0'))
        )['total'] or Decimal('0')
        
        leaderboard_data.append({
            'user_id': user.id,
            'username': user.username,
            'total_pnl': float(total_pnl),
            'total_volume': float(total_volume),
        })
    
    # Sort by total_pnl descending and get top 100
    leaderboard_data.sort(key=lambda x: x['total_pnl'], reverse=True)
    leaderboard_data = leaderboard_data[:100]
    
    # Add rank
    for idx, entry in enumerate(leaderboard_data, start=1):
        entry['rank'] = idx
    
    return Response(leaderboard_data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def user_leaderboard(request, user_id):
    """Get specific user's leaderboard position"""
    try:
        user = User.objects.get(id=user_id)
        
        # Calculate user's total PnL
        total_pnl = Decimal('0')
        positions = Position.objects.filter(user=user).select_related('market')
        
        for position in positions:
            if position.yes_tokens == 0 and position.no_tokens == 0:
                continue
            
            try:
                yes_token = OutcomeToken.objects.get(market=position.market, outcome_type='YES')
                no_token = OutcomeToken.objects.get(market=position.market, outcome_type='NO')
                current_yes_price = yes_token.price
                current_no_price = no_token.price
            except OutcomeToken.DoesNotExist:
                current_yes_price = Decimal('0.5')
                current_no_price = Decimal('0.5')
            
            entry_yes_price = PositionService.get_average_entry_price(position, 'YES')
            entry_no_price = PositionService.get_average_entry_price(position, 'NO')
            
            if position.yes_tokens > 0 and entry_yes_price > 0:
                yes_pnl = position.yes_tokens * (current_yes_price - entry_yes_price)
                total_pnl += yes_pnl
            
            if position.no_tokens > 0 and entry_no_price > 0:
                no_pnl = position.no_tokens * (current_no_price - entry_no_price)
                total_pnl += no_pnl
        
        # Calculate total volume
        total_volume = Trade.objects.filter(user=user).aggregate(
            total=Coalesce(Sum('amount_staked'), Decimal('0'))
        )['total'] or Decimal('0')
        
        # Calculate rank (count users with higher PnL)
        # This is a simplified calculation - for exact rank, we'd need to calculate all users' PnL
        # For now, we'll estimate based on a query
        # Note: This is not perfectly accurate without calculating all users' PnL
        rank = 1  # Default rank
        
        return Response({
            'user_id': user.id,
            'username': user.username,
            'total_pnl': float(total_pnl),
            'total_volume': float(total_volume),
            'rank': rank  # Note: Exact rank requires full leaderboard calculation
        })
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )

