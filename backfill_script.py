from backend_api.api.markets.models import Market
from backend_api.api.liquidity.models import LiquidityEvent
from django.contrib.auth import get_user_model
import random
from decimal import Decimal

print("Starting Backfill...")

markets = Market.objects.all()
admin = get_user_model().objects.filter(is_superuser=True).first()
if not admin:
    admin = get_user_model().objects.first()

if not admin:
    print("No users found. Skipping.")
else:
    events = []
    print(f"Processing {len(markets)} markets...")
    for m in markets:
        # Initial Liquidity
        events.append(LiquidityEvent(
            market=m,
            user=admin,
            event_type='add',
            amount=m.liquidity_pool if m.liquidity_pool else Decimal('1000.00'),
            onchain_tx_hash=f"0x{random.randint(100000,999999)}",
            onchain_liquidity_id=random.randint(1, 10000)
        ))
        
        # Random adds/removes
        if random.random() < 0.3:
            events.append(LiquidityEvent(
                market=m,
                user=admin,
                event_type='remove' if random.random() < 0.5 else 'add',
                amount=Decimal(random.randint(100, 500)),
                 onchain_tx_hash=f"0x{random.randint(100000,999999)}",
                 onchain_liquidity_id=random.randint(10001, 20000)
            ))
    
    LiquidityEvent.objects.bulk_create(events)
    print(f"SUCCESS: Created {len(events)} liquidity events.")
