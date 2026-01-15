from django.core.management.base import BaseCommand
from django.utils import timezone
from backend_api.api.users.models import User
from backend_api.api.trades.models import Trade
from backend_api.api.markets.models import Market, MarketCategory
from ml_service.training.models import TradeRiskPrediction
from security_engine.models import SecurityLog
import random
import uuid
from datetime import timedelta

class Command(BaseCommand):
    help = 'Seeds the database with realistic "Final Phase" data.'

    def handle(self, *args, **options):
        self.stdout.write("Starting Final Seed...")

        # 0. Cleanup (Optional, but good for "Resurrection")
        # Trade.objects.all().delete()
        # TradeRiskPrediction.objects.all().delete()
        # SecurityLog.objects.all().delete()
        # User.objects.filter(is_staff=False).delete() 

        # 1. Ensure Markets Exist
        category, _ = MarketCategory.objects.get_or_create(name="Crypto", defaults={'slug': 'crypto'})

        market, _ = Market.objects.get_or_create(
            title="Will Bitcoin hit $100k in 2025?",
            defaults={
                'description': 'BTC Price Prediction',
                'category': category,
                'status': 'active',
                'ends_at': timezone.now() + timedelta(days=365)
            }
        )

        names = [
            # Azerbaijani / Turkish
            "Aydin", "Leyla", "Orkhan", "Nigar", "Elchin", "Gunel", "Tural", "Sevinj",
            "Mehmet", "Ayse", "Can", "Zeynep", "Emre", "Fatma", "Burak", "Selin",
            # Korean
            "Min-Jun", "Seo-Yeon", "Do-Hyun", "Ji-Woo", "Ha-Eun", "Ju-Won",
            # English / International
            "Alex", "Sarah", "Michael", "Emma", "David", "Olivia", "James", "Sophia"
        ]

        # 2. Create/Get Users (Whales, Moderate, Risky)
        users = []
        
        # 10 Whales
        for i in range(10):
            username = f"{random.choice(names)}_{random.randint(1000,9999)}_Whale"
            u = self.create_user(username, True)
            users.append(u)

        # 20 Moderate
        for i in range(20):
            username = f"{random.choice(names)}_{random.randint(1000,9999)}_Trader"
            u = self.create_user(username, False)
            users.append(u)
            
        # 20 Low/Risky
        risky_users = []
        for i in range(20):
            username = f"{random.choice(names)}_{random.randint(1000,9999)}_Bot"
            u = self.create_user(username, False)
            risky_users.append(u)

        self.stdout.write(self.style.SUCCESS(f"Created/Verified {len(users) + len(risky_users)} Users"))

        # 3. Create Trades (Leaderboard Data)
        count = 0
        for u in users:
            # Whales make big trades
            is_whale = "Whale" in u.username
            num_trades = random.randint(10, 50) if is_whale else random.randint(1, 10)
            
            for _ in range(num_trades):
                amount = random.uniform(1000, 50000) if is_whale else random.uniform(10, 500)
                price = random.uniform(0.1, 0.9)
                Trade.objects.create(
                    user=u,
                    market=market,
                    amount_staked=amount,
                    outcome_type="YES" if random.random() > 0.4 else "NO",
                    trade_type="buy" if random.random() > 0.5 else "sell",
                    price_at_execution=price,
                    tokens_amount=amount / price,
                    created_at=timezone.now() - timedelta(days=random.randint(0, 30))
                )
                count += 1
        
        self.stdout.write(self.style.SUCCESS(f"Created {count} Trades"))

        # 4. ML & Security Logs
        # Create Risky Predictions
        for u in risky_users:
            # High Risk Score
            TradeRiskPrediction.objects.create(
                user_id=u.id,
                market_id=market.id,
                score=random.uniform(0.85, 0.99),
                label=-1,
                risk_level="HIGH",
                created_at=timezone.now() - timedelta(minutes=random.randint(1, 600))
            )
            # Security Log
            SecurityLog.objects.create(
                user=u,
                event_type="SUSPICIOUS_ACTIVITY",
                severity="HIGH",
                message="Abnormal trading velocity detected.",
                ip=f"192.168.1.{random.randint(1, 255)}"
            )
            
        # Create some DDoS logs (No user)
        for _ in range(10):
            l = SecurityLog.objects.create(
                event_type="DDOS_ATTEMPT",
                severity="CRITICAL",
                message="Rate limit exceeded from subnet 10.0.0.x",
                ip="10.0.0.5"
            )
            l.timestamp = timezone.now() - timedelta(minutes=random.randint(1, 100))
            l.save()

        self.stdout.write(self.style.SUCCESS("Seeding Complete."))

    def create_user(self, username, is_whale):
        # Helper to get or create with wallet
        try:
            u = User.objects.get(username=username)
        except User.DoesNotExist:
            u = User.objects.create(username=username, email=f"{username.lower()}@example.com")
            u.set_password("password123")
            
        # Ensure wallet
        if not u.wallet_address:
            u.wallet_address = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex}"[:42]
        
        # Set dummy earnings/points for Leaderboard
        points = random.uniform(1000, 5000) if is_whale else random.uniform(0, 500)
        
        if hasattr(u, 'total_earnings'):
             u.total_earnings = points
             
        if hasattr(u, 'total_points'):
             u.total_points = points
             
        if hasattr(u, 'win_rate'):
             u.win_rate = random.uniform(0.7, 0.9) if is_whale else random.uniform(0.4, 0.6)
             
        if hasattr(u, 'streak'):
             u.streak = random.randint(1, 10) if is_whale else random.randint(0, 2)
             
        u.save()
        return u

