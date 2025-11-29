"""
Quick script to verify seeded data.
Run with: python manage.py shell < verify_seed.py
Or: docker-compose exec web python manage.py shell < verify_seed.py
"""
from markets.models import Market, MarketCategory, OutcomeToken, PriceHistory, Resolution
from users.models import User
from trades.models import Trade
from positions.models import Position
from liquidity.models import LiquidityEvent
from disputes.models import Dispute
from indexer.models import OnchainTransaction, OnchainEventLog

print("\n" + "="*60)
print("DATABASE SEED VERIFICATION")
print("="*60)

# Count all models
counts = {
    'Market Categories': MarketCategory.objects.count(),
    'Users': User.objects.count(),
    'Markets': Market.objects.count(),
    'Outcome Tokens': OutcomeToken.objects.count(),
    'Trades': Trade.objects.count(),
    'Positions': Position.objects.count(),
    'Liquidity Events': LiquidityEvent.objects.count(),
    'Disputes': Dispute.objects.count(),
    'Resolutions': Resolution.objects.count(),
    'Price History': PriceHistory.objects.count(),
    'Onchain Transactions': OnchainTransaction.objects.count(),
    'Onchain Event Logs': OnchainEventLog.objects.count(),
}

for name, count in counts.items():
    status = "✓" if count > 0 else "✗"
    print(f"{status} {name}: {count}")

print("\n" + "="*60)
print("SAMPLE DATA")
print("="*60)

# Show sample markets
print("\n📊 Markets:")
for market in Market.objects.all()[:3]:
    print(f"  - {market.title} ({market.status})")

# Show sample users
print("\n👥 Users:")
for user in User.objects.all()[:3]:
    print(f"  - {user.username} ({user.email}) - {user.total_points} points")

# Show sample trades
print("\n💱 Trades:")
for trade in Trade.objects.all()[:3]:
    print(f"  - {trade.user.username}: {trade.trade_type} {trade.outcome_type} on {trade.market.title[:40]}...")

print("\n" + "="*60)
print("Verification complete!")
print("="*60 + "\n")

