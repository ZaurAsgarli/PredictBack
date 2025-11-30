"""
Celery tasks for trades
"""
from celery import shared_task
from django.utils import timezone
from markets.models import Market
from positions.models import Position


@shared_task
def settle_market_positions(market_id, resolved_outcome):
    """Settle all positions when a market is resolved"""
    try:
        market = Market.objects.get(id=market_id)
        positions = Position.objects.filter(market=market)
        
        for position in positions:
            user = position.user
            
            if resolved_outcome == 'YES':
                # Users with YES tokens win
                winnings = position.yes_tokens
                loss = position.no_tokens
            else:  # NO
                # Users with NO tokens win
                winnings = position.no_tokens
                loss = position.yes_tokens
            
            # Update user stats
            if winnings > loss:
                user.total_points += (winnings - loss)
                user.streak += 1
            else:
                user.streak = 0
            
            # Calculate win rate
            total_trades = user.trades.count()
            if total_trades > 0:
                wins = user.trades.filter(
                    market__status='resolved',
                    outcome_type=resolved_outcome
                ).count()
                user.win_rate = (wins / total_trades) * 100
            
            user.save()
    
    except Market.DoesNotExist:
        pass

