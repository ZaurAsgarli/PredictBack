from django.core.management.base import BaseCommand
from django.utils import timezone
from backend_api.api.users.models import User
from backend_api.api.trades.models import Trade
from backend_api.api.markets.models import Market, MarketCategory, OutcomeToken
from ml_service.training.models import TradeRiskPrediction
from security_engine.models import SecurityLog
from datetime import timedelta
import random
import uuid
from decimal import Decimal

class Command(BaseCommand):
    help = 'Seeds EVERYTHING: Users, Markets, Trades, Logs (Fail-Safe)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("=" * 60))
        self.stdout.write(self.style.WARNING("COMPREHENSIVE DATABASE SEEDING"))
        self.stdout.write(self.style.WARNING("=" * 60))
        
        # ============================================================
        # STEP 1: USERS (THE FOUNDATION)
        # ============================================================
        self.stdout.write(self.style.SUCCESS("\n[STEP 1] Creating Users..."))
        
        users_created = []
        
        # 1.1 Superuser
        try:
            admin = User.objects.get(username='admin')
            self.stdout.write(f"  ✓ Admin exists: {admin.username}")
        except User.DoesNotExist:
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@predicthub.io',
                password='admin123',
                role=User.Role.ADMIN
            )
            self.stdout.write(self.style.SUCCESS(f"  ✓ Created Superuser: {admin.username}"))
        
        # 1.2 Whales (5)
        whale_names = ["MobyDick", "Orca", "BlueWhale", "Leviathan", "Poseidon"]
        for name in whale_names:
            u, created = User.objects.get_or_create(
                username=name,
                defaults={
                    'email': f'{name.lower()}@whales.io',
                    'role': User.Role.WHALE,
                    'wallet_address': f'0x{uuid.uuid4().hex[:40]}',
                    'total_points': Decimal(random.uniform(5000, 15000)),
                    'win_rate': Decimal(random.uniform(0.75, 0.95)),
                    'streak': random.randint(5, 15)
                }
            )
            if created:
                u.set_password('whale123')
                u.save()
            users_created.append(u)
            self.stdout.write(f"  ✓ Whale: {u.username}")
        
        # 1.3 Blocked Bots (5)
        blocked_bots = []
        for i in range(5):
            u, created = User.objects.get_or_create(
                username=f'SuspiciousBot_{i+1}',
                defaults={
                    'email': f'bot{i+1}@malicious.io',
                    'role': User.Role.BLOCKED,
                    'is_active': False,
                    'wallet_address': f'0x{uuid.uuid4().hex[:40]}',
                    'total_points': Decimal(0),
                    'win_rate': Decimal(0),
                    'streak': 0
                }
            )
            if created:
                u.set_password('blocked')
                u.save()
            blocked_bots.append(u)
            self.stdout.write(f"  ✓ Blocked Bot: {u.username}")
        
        # 1.4 Regular Traders (40)
        trader_names = [
            "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry",
            "Ivy", "Jack", "Kate", "Liam", "Mia", "Noah", "Olivia", "Paul",
            "Quinn", "Ruby", "Sam", "Tina", "Uma", "Victor", "Wendy", "Xander",
            "Yara", "Zane", "Amy", "Ben", "Cara", "Dan", "Ella", "Finn",
            "Gina", "Hugo", "Iris", "Jake", "Luna", "Max", "Nina", "Oscar"
        ]
        
        for name in trader_names:
            u, created = User.objects.get_or_create(
                username=f'{name}_Trader',
                defaults={
                    'email': f'{name.lower()}@traders.io',
                    'role': User.Role.TRADER,
                    'wallet_address': f'0x{uuid.uuid4().hex[:40]}',
                    'total_points': Decimal(random.uniform(100, 2000)),
                    'win_rate': Decimal(random.uniform(0.40, 0.70)),
                    'streak': random.randint(0, 5)
                }
            )
            if created:
                u.set_password('trader123')
                u.save()
            users_created.append(u)
        
        self.stdout.write(self.style.SUCCESS(f"  ✅ Total Users Created: {len(users_created) + len(blocked_bots) + 1}"))
        
        # ============================================================
        # STEP 2: MARKETS (THE PRODUCT)
        # ============================================================
        self.stdout.write(self.style.SUCCESS("\n[STEP 2] Creating Markets..."))
        
        # 2.1 Ensure Category
        category, _ = MarketCategory.objects.get_or_create(
            name="Crypto",
            defaults={'slug': 'crypto', 'description': 'Cryptocurrency predictions'}
        )
        
        markets_active = []
        markets_resolved = []
        
        # 2.2 Active Markets (5)
        active_market_data = [
            ("Will Bitcoin reach $100,000 in 2026?", "BTC price prediction for year-end 2026"),
            ("Will Ethereum outperform Bitcoin in Q2 2026?", "ETH vs BTC returns comparison"),
            ("Will Solana maintain top 10 market cap?", "SOL market position"),
            ("Will a new crypto ETF be approved in 2026?", "Regulatory approval prediction"),
            ("Will DeFi TVL exceed $200B in 2026?", "Total Value Locked growth")
        ]
        
        for title, desc in active_market_data:
            m, created = Market.objects.get_or_create(
                title=title,
                defaults={
                    'description': desc,
                    'category': category,
                    'status': 'active',
                    'liquidity_pool': Decimal('10000.00'),  # CRITICAL: Initialize liquidity
                    'fee_percentage': Decimal('0.02'),
                    'ends_at': timezone.now() + timedelta(days=random.randint(30, 365)),
                    'created_by': admin
                }
            )
            markets_active.append(m)
            
            # Create Outcome Tokens
            OutcomeToken.objects.get_or_create(
                market=m,
                outcome_type='YES',
                defaults={'price': Decimal('0.50'), 'supply': Decimal('5000.00')}
            )
            OutcomeToken.objects.get_or_create(
                market=m,
                outcome_type='NO',
                defaults={'price': Decimal('0.50'), 'supply': Decimal('5000.00')}
            )
            
            self.stdout.write(f"  ✓ Active Market: {m.title[:50]}...")
        
        # 2.3 Resolved Markets (3)
        resolved_market_data = [
            ("Did Trump win the 2024 election?", "US Presidential Election", "YES"),
            ("Did Bitcoin hit $50k in 2024?", "BTC milestone", "YES"),
            ("Was there a major exchange hack in 2024?", "Security event", "NO")
        ]
        
        for title, desc, outcome in resolved_market_data:
            m, created = Market.objects.get_or_create(
                title=title,
                defaults={
                    'description': desc,
                    'category': category,
                    'status': 'resolved',
                    'resolution_outcome': outcome,
                    'liquidity_pool': Decimal('8000.00'),
                    'fee_percentage': Decimal('0.02'),
                    'ends_at': timezone.now() - timedelta(days=random.randint(30, 90)),
                    'created_by': admin
                }
            )
            markets_resolved.append(m)
            self.stdout.write(f"  ✓ Resolved Market: {m.title[:50]}... [{outcome}]")
        
        self.stdout.write(self.style.SUCCESS(f"  ✅ Total Markets: {len(markets_active) + len(markets_resolved)}"))
        
        # ============================================================
        # STEP 3: TRADES (THE ACTION)
        # ============================================================
        self.stdout.write(self.style.SUCCESS("\n[STEP 3] Creating Trades..."))
        
        total_trades = 0
        
        # Only active users trade
        active_users = [u for u in users_created if u.is_active]
        
        for user in active_users:
            num_trades = random.randint(5, 15) if user.role == User.Role.WHALE else random.randint(2, 8)
            
            for _ in range(num_trades):
                # Pick random active market
                market = random.choice(markets_active)
                
                # Trade params
                is_whale = user.role == User.Role.WHALE
                amount = Decimal(random.uniform(1000, 10000) if is_whale else random.uniform(50, 500))
                price = Decimal(random.uniform(0.30, 0.70))
                outcome = random.choice(['YES', 'NO'])
                trade_type = random.choice(['buy', 'sell'])
                
                # Create Trade
                Trade.objects.create(
                    user=user,
                    market=market,
                    outcome_type=outcome,
                    trade_type=trade_type,
                    amount_staked=amount,
                    tokens_amount=amount / price,
                    price_at_execution=price,
                    created_at=timezone.now() - timedelta(days=random.randint(0, 30))
                )
                
                # Update user stats (CRITICAL for Leaderboard)
                user.total_points += amount * Decimal(random.uniform(0.1, 0.3))  # Simulated earnings
                total_trades += 1
            
            # Recalculate win_rate based on trades
            user_trades = Trade.objects.filter(user=user)
            if user_trades.count() > 0:
                # Simulate wins (whales have higher win rate)
                wins = int(user_trades.count() * (0.80 if is_whale else 0.55))
                user.win_rate = Decimal(wins / user_trades.count())
            
            user.save()
        
        self.stdout.write(self.style.SUCCESS(f"  ✅ Total Trades Created: {total_trades}"))
        
        # ============================================================
        # STEP 4: LOGS (THE INTELLIGENCE)
        # ============================================================
        self.stdout.write(self.style.SUCCESS("\n[STEP 4] Creating Intelligence Logs..."))
        
        # 4.1 Security Logs (20)
        security_events = [
            ("RATE_LIMIT", "HIGH", "Excessive requests from IP 192.168.1.100"),
            ("FAILED_LOGIN", "MEDIUM", "Failed login attempt for user {}"),
            ("SUSPICIOUS_ACTIVITY", "CRITICAL", "Abnormal trading pattern detected"),
            ("UNAUTHORIZED_ACCESS", "HIGH", "Attempted access to admin panel"),
        ]
        
        for i in range(20):
            event_type, severity, msg_template = random.choice(security_events)
            
            SecurityLog.objects.create(
                user=random.choice(active_users) if random.random() > 0.3 else None,
                event_type=event_type,
                severity=severity,
                message=msg_template.format(random.choice(active_users).username if '{}' in msg_template else ''),
                ip=f"192.168.{random.randint(1,255)}.{random.randint(1,255)}",
                timestamp=timezone.now() - timedelta(hours=random.randint(1, 72))
            )
        
        self.stdout.write(f"  ✓ Created 20 Security Logs")
        
        # 4.2 ML Risk Predictions (20)
        for i in range(20):
            user = random.choice(active_users + blocked_bots)
            market = random.choice(markets_active)
            
            # Blocked bots have high risk
            is_risky = user.role == User.Role.BLOCKED
            
            TradeRiskPrediction.objects.create(
                user_id=user.id,
                market_id=market.id,
                score=random.uniform(0.90, 0.99) if is_risky else random.uniform(0.10, 0.40),
                label=-1 if is_risky else 1,
                risk_level="HIGH" if is_risky else "LOW",
                created_at=timezone.now() - timedelta(hours=random.randint(1, 48))
            )
        
        self.stdout.write(f"  ✓ Created 20 ML Risk Predictions")
        
        # ============================================================
        # FINAL SUMMARY
        # ============================================================
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("✅ DATABASE SEEDING COMPLETE"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"  Users: {User.objects.count()}")
        self.stdout.write(f"  Markets: {Market.objects.count()}")
        self.stdout.write(f"  Trades: {Trade.objects.count()}")
        self.stdout.write(f"  Security Logs: {SecurityLog.objects.count()}")
        self.stdout.write(f"  ML Predictions: {TradeRiskPrediction.objects.count()}")
        self.stdout.write(self.style.SUCCESS("=" * 60))
