from django.core.management.base import BaseCommand
from ml_service.training.models import TradeRiskPrediction
from backend_api.api.users.models import User
from backend_api.api.markets.models import Market
from django.utils import timezone
import random

class Command(BaseCommand):
    help = 'Simulates Good and Bad traffic to populate Risk Logs'

    def handle(self, *args, **options):
        self.stdout.write("Simulating Risk Scenarios...")
        
        # Ensure at least one user/market exists (Mocking IDs if DB empty)
        # In production/test, you'd fetch real ones.
        user_id = 999
        market_id = 1
        
        # 1. Simulate Good Traffic (Approved)
        self.stdout.write("- Generating 5 Good Trades...")
        for i in range(5):
            TradeRiskPrediction.objects.create(
                user_id=user_id,
                market_id=market_id,
                score=random.uniform(0.1, 0.4), # Low Score
                label=1, # Normal
                risk_level="LOW",
                created_at=timezone.now()
            )

        # 2. Simulate Attacks (Blocked)
        self.stdout.write("- Generating 3 Attacks...")
        for i in range(3):
            TradeRiskPrediction.objects.create(
                user_id=user_id,
                market_id=market_id,
                score=random.uniform(0.86, 0.99), # HIGH Score (>0.85)
                label=-1, # Anomaly
                risk_level="HIGH",
                created_at=timezone.now()
            )
            
        self.stdout.write(self.style.SUCCESS("Successfully populated TradeRiskPrediction table."))
