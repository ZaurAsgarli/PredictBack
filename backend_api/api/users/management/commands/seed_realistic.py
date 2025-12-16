from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from backend_api.api.markets.polymarket_service import PolymarketService
from backend_api.api.markets.models import Market
from backend_api.api.trades.models import Trade
from backend_api.api.users.models import User
from security_engine.models import SecurityLog, LoginAttempt
from ml_service.training.models import TradeRiskPrediction
import random
from faker import Faker
from decimal import Decimal

class Command(BaseCommand):
    help = 'Seeds the database with realistic demo data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Realistic Seeding...'))
        
        # 1. Sync Polymarket Data
        self.stdout.write('Syncing Polymarket Data...')
        service = PolymarketService()
        count = service.sync_markets()
        self.stdout.write(f'Synced {count} markets.')

        # 2. Create Users
        fake = Faker()
        nationalities = {
            'az': ['Anar', 'Gunel', 'Tural', 'Leyla', 'Rashad', 'Nigar'],
            'tr': ['Burak', 'Zeynep', 'Mehmet', 'Ayse', 'Can', 'Elif'],
            'kr': ['Min-jun', 'Ji-ah', 'Seo-jun', 'Ha-eun'],
            'en': ['James', 'Sarah', 'Michael', 'Emma']
        }
        
        users_created = 0
        all_users = []
        
        for nat, names in nationalities.items():
            for name in names:
                username = f"{name.lower()}_{nat}_{random.randint(100, 999)}"
                email = f"{username}@example.com"
                
                user, created = User.objects.get_or_create(
                    username=username,
                    email=email,
                    defaults={
                        'role': 'user',
                        'total_points': Decimal(random.randint(1000, 50000)), # Simulating "Wallet Balance" in points
                        'wallet_address': f"0x{random.getrandbits(160):040x}",
                        'win_rate': Decimal(random.uniform(30.0, 80.0)),
                    }
                )
                if created:
                    user.set_password('password123')
                    user.save()
                    users_created += 1
                all_users.append(user)

        self.stdout.write(f'Created/Loaded {len(all_users)} users.')

        # 3. Create Trading History
        markets = list(Market.objects.filter(status='active'))
        if not markets:
            self.stdout.write(self.style.WARNING('No active markets found to trade on.'))
        else:
            trades_created = 0
            for user in all_users:
                # each user makes 1-5 trades
                for _ in range(random.randint(1, 5)):
                    market = random.choice(markets)
                    amount = Decimal(random.uniform(10.0, 500.0))
                    outcome = random.choice(['YES', 'NO'])
                    trade_type = random.choice(['buy', 'sell'])
                    
                    Trade.objects.create(
                        user=user,
                        market=market,
                        outcome_type=outcome,
                        trade_type=trade_type,
                        amount_staked=amount,
                        tokens_amount=amount, # simplified
                        price_at_execution=Decimal(random.uniform(0.1, 0.9))
                    )
                    trades_created += 1
            self.stdout.write(f'Generated {trades_created} trades.')

        # 4. Generate Security Logs
        log_types = [
            ('SQL Injection Attempt', 'CRITICAL', 'BLOCKED'),
            ('DDoS Blocked', 'HIGH', 'BLOCKED'),
            ('Rate Limit Exceeded', 'MEDIUM', 'WARNING'),
            ('Failed Login', 'LOW', 'MONITORED')
        ]
        
        logs_created = 0
        for _ in range(200):
            event, severity, status = random.choice(log_types)
            SecurityLog.objects.create(
                event_type=event.upper().replace(' ', '_'),
                severity=severity,
                ip=fake.ipv4(),
                message=f"{event} detected from {fake.country_code()}",
                user=random.choice(all_users) if random.random() > 0.7 else None
            )
            logs_created += 1
        self.stdout.write(f'Generated {logs_created} security logs.')

        # 5. ML Risk Scores (High Risk Users)
        risky_users = random.sample(all_users, k=min(5, len(all_users)))
        for user in risky_users:
            TradeRiskPrediction.objects.create(
                user=user,
                score=random.uniform(0.85, 0.99),
                label=-1, # Anomaly
                risk_level='CRITICAL',
                amount_staked=Decimal(random.uniform(5000, 10000))
            )
        self.stdout.write(f'Flagged {len(risky_users)} users as High Risk.')

        self.stdout.write(self.style.SUCCESS('Seeding Complete!'))
