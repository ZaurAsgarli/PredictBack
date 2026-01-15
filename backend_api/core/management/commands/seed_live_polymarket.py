from django.core.management.base import BaseCommand
from django.utils import timezone
from backend_api.api.users.models import User
from backend_api.api.trades.models import Trade
from backend_api.api.markets.models import Market, MarketCategory, OutcomeToken
from ml_service.training.models import TradeRiskPrediction
from security_engine.models import SecurityLog
from datetime import timedelta, datetime
import random
import uuid
import requests
from decimal import Decimal

class Command(BaseCommand):
    help = 'Seeds database with LIVE Polymarket data + Realistic Users'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("=" * 70))
        self.stdout.write(self.style.WARNING("LIVE POLYMARKET SEEDING PROTOCOL"))
        self.stdout.write(self.style.WARNING("=" * 70))
        
        # ============================================================
        # STEP 1: CREATE REALISTIC USERS (Preserved Logic)
        # ============================================================
        self.stdout.write(self.style.SUCCESS("\n[STEP 1] Creating Realistic User Population..."))
        
        users_created = []
        whale_users = []
        trader_users = []
        blocked_bots = []
        market_makers = []
        
        # 1.1 Superusers (3)
        admin_names = ["admin", "superadmin", "system_admin"]
        for name in admin_names:
            u, created = User.objects.get_or_create(
                username=name,
                defaults={
                    'email': f'{name}@predicthub.io',
                    'role': User.Role.ADMIN,
                    'is_staff': True,
                    'is_superuser': True,
                    'wallet_address': f'0x{uuid.uuid4().hex[:40]}',
                    'total_points': Decimal('0.00'),
                }
            )
            if created:
                u.set_password('admin123')
                u.save()
            self.stdout.write(f"  ✓ Admin: {u.username}")
        
        # 1.2 Whales (10) - High-value traders
        whale_names = [
            "MobyDick", "KrakenLord", "WhaleWatch", "CryptoOrca", "BigDaddy",
            "DiamondHands", "LiquidityKing", "MegaMind", "OceanGiant", "DeepPockets"
        ]
        for name in whale_names:
            u, created = User.objects.get_or_create(
                username=name,
                defaults={
                    'email': f'{name.lower()}@whales.io',
                    'role': User.Role.WHALE,
                    'wallet_address': f'0x{uuid.uuid4().hex[:40]}',
                    'total_points': Decimal(random.uniform(50000, 150000)),
                    'win_rate': Decimal(random.uniform(0.70, 0.90)),
                    'streak': random.randint(10, 25)
                }
            )
            if created:
                u.set_password('whale123')
                u.save()
            whale_users.append(u)
            users_created.append(u)
            self.stdout.write(f"  ✓ Whale: {u.username}")
        
        # 1.3 Market Makers (10) - Liquidity providers
        mm_names = [
            "MM_Genesis", "MM_Citadel", "MM_Galaxy", "MM_Voyager", "MM_Nexus",
            "MM_Quantum", "MM_Alpha", "MM_Omega", "MM_Sigma", "MM_Delta"
        ]
        for name in mm_names:
            u, created = User.objects.get_or_create(
                username=name,
                defaults={
                    'email': f'{name.lower()}@marketmakers.io',
                    'role': User.Role.TRADER,  # Market makers are advanced traders
                    'wallet_address': f'0x{uuid.uuid4().hex[:40]}',
                    'total_points': Decimal(random.uniform(20000, 50000)),
                    'win_rate': Decimal(random.uniform(0.65, 0.80)),
                    'streak': random.randint(5, 15)
                }
            )
            if created:
                u.set_password('mm123')
                u.save()
            market_makers.append(u)
            users_created.append(u)
        
        self.stdout.write(f"  ✓ Created {len(market_makers)} Market Makers")
        
        # 1.4 Regular Traders (100)
        trader_names = [
            "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry",
            "Ivy", "Jack", "Kate", "Liam", "Mia", "Noah", "Olivia", "Paul",
            "Quinn", "Ruby", "Sam", "Tina", "Uma", "Victor", "Wendy", "Xander",
            "Yara", "Zane", "Amy", "Ben", "Cara", "Dan", "Ella", "Finn",
            "Gina", "Hugo", "Iris", "Jake", "Luna", "Max", "Nina", "Oscar",
            "Pam", "Quincy", "Ron", "Sara", "Tom", "Ursula", "Vince", "Will",
            "Xena", "Yuki", "Zara", "Adam", "Beth", "Carl", "Dora", "Eric",
            "Faye", "Greg", "Hana", "Ivan", "Jill", "Kyle", "Lily", "Mark",
            "Nora", "Owen", "Pearl", "Quest", "Rita", "Steve", "Tara", "Umar",
            "Vera", "Wade", "Xiu", "Yale", "Zoe", "Alan", "Bella", "Chris",
            "Daisy", "Ethan", "Fiona", "Gary", "Helen", "Isaac", "Jane", "Kevin",
            "Laura", "Mike", "Nancy", "Oliver", "Penny", "Quinton", "Rachel", "Simon",
            "Tracy", "Urban", "Violet", "Walter", "Yvonne", "Zachary", "Amber"
        ]
        
        for name in trader_names:
            u, created = User.objects.get_or_create(
                username=f'{name}_Trader',
                defaults={
                    'email': f'{name.lower()}@traders.io',
                    'role': User.Role.TRADER,
                    'wallet_address': f'0x{uuid.uuid4().hex[:40]}',
                    'total_points': Decimal(random.uniform(500, 5000)),
                    'win_rate': Decimal(random.uniform(0.45, 0.65)),
                    'streak': random.randint(0, 8)
                }
            )
            if created:
                u.set_password('trader123')
                u.save()
            trader_users.append(u)
            users_created.append(u)
        
        self.stdout.write(f"  ✓ Created {len(trader_users)} Regular Traders")
        
        # 1.5 Malicious Bots (20)
        for i in range(20):
            u, created = User.objects.get_or_create(
                username=f'MaliciousBot_{i+1:03d}',
                defaults={
                    'email': f'bot{i+1}@malicious.net',
                    'role': User.Role.BLOCKED,
                    'is_active': False,
                    'wallet_address': f'0x{uuid.uuid4().hex[:40]}',
                    'total_points': Decimal('0.00'),
                    'win_rate': Decimal('0.00'),
                    'streak': 0
                }
            )
            if created:
                u.set_password('blocked')
                u.save()
            blocked_bots.append(u)
        
        self.stdout.write(f"  ✓ Created {len(blocked_bots)} Blocked Bots")
        self.stdout.write(self.style.SUCCESS(f"  ✅ Total Users: {User.objects.count()}"))
        
        # ============================================================
        # STEP 2: FETCH LIVE POLYMARKET DATA
        # ============================================================
        self.stdout.write(self.style.SUCCESS("\n[STEP 2] Fetching Live Markets from Polymarket..."))
        
        markets_created = []
        
        try:
            # Fetch from Polymarket Gamma API
            url = "https://gamma-api.polymarket.com/events"
            params = {
                'active': 'true',
                'closed': 'false',
                'limit': 20,
                'order': 'volume24hr',
                'ascending': 'false'
            }
            
            self.stdout.write(f"  → Requesting: {url}")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            events = response.json()
            self.stdout.write(f"  ✓ Fetched {len(events)} events from Polymarket")
            
            # Process each event
            for idx, event in enumerate(events):
                try:
                    # Extract data
                    title = event.get('title', f'Market {idx+1}')
                    description = event.get('description', '')[:500]  # Limit length
                    
                    # Category from tags
                    tags = event.get('tags', [])
                    category_name = tags[0].get('label', 'Other') if tags else 'Other'
                    
                    # Get or create category
                    category, _ = MarketCategory.objects.get_or_create(
                        name=category_name,
                        defaults={'slug': category_name.lower().replace(' ', '-')}
                    )
                    
                    # End date
                    end_date_str = event.get('endDate')
                    if end_date_str:
                        try:
                            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                        except:
                            end_date = timezone.now() + timedelta(days=random.randint(30, 365))
                    else:
                        end_date = timezone.now() + timedelta(days=random.randint(30, 365))
                    
                    # Volume (convert to liquidity pool)
                    volume = float(event.get('volume', 0))
                    liquidity = Decimal(max(volume * 0.1, 5000))  # Use 10% of volume or min $5k
                    
                    # Create market
                    market, created = Market.objects.get_or_create(
                        title=title[:200],  # Limit to field max length
                        defaults={
                            'description': description,
                            'category': category,
                            'status': 'active',
                            'liquidity_pool': liquidity,
                            'fee_percentage': Decimal('0.02'),
                            'ends_at': end_date,
                            'created_by': User.objects.filter(is_superuser=True).first()
                        }
                    )
                    
                    if created:
                        # Create outcome tokens
                        OutcomeToken.objects.get_or_create(
                            market=market,
                            outcome_type='YES',
                            defaults={'price': Decimal('0.50'), 'supply': liquidity / 2}
                        )
                        OutcomeToken.objects.get_or_create(
                            market=market,
                            outcome_type='NO',
                            defaults={'price': Decimal('0.50'), 'supply': liquidity / 2}
                        )
                    
                    markets_created.append(market)
                    self.stdout.write(f"  ✓ [{category_name}] {title[:60]}...")
                    
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"  ⚠ Skipped event: {str(e)}"))
                    continue
            
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f"  ✗ API Error: {str(e)}"))
            self.stdout.write(self.style.WARNING("  → Falling back to hardcoded markets..."))
            
            # FALLBACK: Hardcoded realistic markets
            fallback_markets = [
                ("Presidential Election 2028", "Politics", "Who will win?", 180),
                ("Bitcoin above $100k in 2026?", "Crypto", "BTC price prediction", 365),
                ("Super Bowl LIX Winner", "Sports", "NFL Championship", 45),
                ("Ethereum ETF Approval", "Crypto", "SEC decision", 90),
                ("Next James Bond Actor", "Pop Culture", "007 casting", 120),
            ]
            
            for title, cat_name, desc, days in fallback_markets:
                category, _ = MarketCategory.objects.get_or_create(
                    name=cat_name,
                    defaults={'slug': cat_name.lower()}
                )
                
                market, created = Market.objects.get_or_create(
                    title=title,
                    defaults={
                        'description': desc,
                        'category': category,
                        'status': 'active',
                        'liquidity_pool': Decimal(random.uniform(10000, 50000)),
                        'ends_at': timezone.now() + timedelta(days=days),
                        'created_by': User.objects.filter(is_superuser=True).first()
                    }
                )
                
                if created:
                    OutcomeToken.objects.get_or_create(
                        market=market,
                        outcome_type='YES',
                        defaults={'price': Decimal('0.50'), 'supply': market.liquidity_pool / 2}
                    )
                    OutcomeToken.objects.get_or_create(
                        market=market,
                        outcome_type='NO',
                        defaults={'price': Decimal('0.50'), 'supply': market.liquidity_pool / 2}
                    )
                
                markets_created.append(market)
        
        self.stdout.write(self.style.SUCCESS(f"  ✅ Total Markets: {len(markets_created)}"))
        
        # ============================================================
        # STEP 3: SIMULATE TRADING ECOSYSTEM
        # ============================================================
        self.stdout.write(self.style.SUCCESS("\n[STEP 3] Simulating Trading Activity..."))
        
        total_trades = 0
        
        # 3.1 High-conviction markets (top 5 by liquidity)
        high_volume_markets = sorted(markets_created, key=lambda m: m.liquidity_pool, reverse=True)[:5]
        
        # Whales trade on high-volume markets
        for whale in whale_users:
            num_trades = random.randint(15, 30)
            
            for _ in range(num_trades):
                market = random.choice(high_volume_markets if random.random() > 0.3 else markets_created)
                
                amount = Decimal(random.uniform(1000, 10000))
                price = Decimal(random.uniform(0.35, 0.65))
                outcome = 'YES' if random.random() > 0.3 else 'NO'  # Bullish bias
                
                Trade.objects.create(
                    user=whale,
                    market=market,
                    outcome_type=outcome,
                    trade_type=random.choice(['buy', 'sell']),
                    amount_staked=amount,
                    tokens_amount=amount / price,
                    price_at_execution=price,
                    created_at=timezone.now() - timedelta(days=random.randint(0, 30))
                )
                
                whale.total_points += amount * Decimal(random.uniform(0.05, 0.15))
                total_trades += 1
            
            whale.save()
        
        # Market Makers provide liquidity across all markets
        for mm in market_makers:
            num_trades = random.randint(20, 40)
            
            for _ in range(num_trades):
                market = random.choice(markets_created)
                
                amount = Decimal(random.uniform(500, 2000))
                price = Decimal(random.uniform(0.45, 0.55))  # Near 50/50
                
                Trade.objects.create(
                    user=mm,
                    market=market,
                    outcome_type=random.choice(['YES', 'NO']),
                    trade_type=random.choice(['buy', 'sell']),
                    amount_staked=amount,
                    tokens_amount=amount / price,
                    price_at_execution=price,
                    created_at=timezone.now() - timedelta(days=random.randint(0, 30))
                )
                
                mm.total_points += amount * Decimal(random.uniform(0.02, 0.08))
                total_trades += 1
            
            mm.save()
        
        # Regular traders
        for trader in trader_users[:50]:  # First 50 active traders
            num_trades = random.randint(3, 10)
            
            for _ in range(num_trades):
                market = random.choice(markets_created)
                
                amount = Decimal(random.uniform(50, 500))
                price = Decimal(random.uniform(0.30, 0.70))
                
                Trade.objects.create(
                    user=trader,
                    market=market,
                    outcome_type=random.choice(['YES', 'NO']),
                    trade_type='buy',
                    amount_staked=amount,
                    tokens_amount=amount / price,
                    price_at_execution=price,
                    created_at=timezone.now() - timedelta(days=random.randint(0, 30))
                )
                
                trader.total_points += amount * Decimal(random.uniform(0.01, 0.10))
                total_trades += 1
            
            trader.save()
        
        self.stdout.write(self.style.SUCCESS(f"  ✅ Total Trades: {total_trades}"))
        
        # ============================================================
        # STEP 4: INTELLIGENCE LOGS
        # ============================================================
        self.stdout.write(self.style.SUCCESS("\n[STEP 4] Generating Intelligence Logs..."))
        
        # 4.1 Security Logs (150+)
        security_events = [
            ("RATE_LIMIT", "HIGH", "Rate limit exceeded from {}"),
            ("FAILED_LOGIN", "MEDIUM", "Failed login attempt for {}"),
            ("SUSPICIOUS_ACTIVITY", "CRITICAL", "High-velocity trading detected: {}"),
            ("UNAUTHORIZED_ACCESS", "HIGH", "Unauthorized API access attempt"),
        ]
        
        for i in range(150):
            event_type, severity, msg_template = random.choice(security_events)
            user = random.choice(users_created + blocked_bots) if random.random() > 0.2 else None
            
            SecurityLog.objects.create(
                user=user,
                event_type=event_type,
                severity=severity,
                message=msg_template.format(user.username if user and '{}' in msg_template else f"IP {random.randint(1,255)}"),
                ip=f"192.168.{random.randint(1,255)}.{random.randint(1,255)}",
                timestamp=timezone.now() - timedelta(hours=random.randint(1, 168))
            )
        
        self.stdout.write(f"  ✓ Created 150 Security Logs")
        
        # 4.2 ML Risk Predictions (150+)
        for i in range(150):
            user = random.choice(users_created + blocked_bots)
            market = random.choice(markets_created)
            
            is_risky = user in blocked_bots or random.random() < 0.15
            
            TradeRiskPrediction.objects.create(
                user_id=user.id,
                market_id=market.id,
                score=random.uniform(0.88, 0.99) if is_risky else random.uniform(0.10, 0.45),
                label=-1 if is_risky else 1,
                risk_level="HIGH" if is_risky else "LOW",
                created_at=timezone.now() - timedelta(hours=random.randint(1, 72))
            )
        
        self.stdout.write(f"  ✓ Created 150 ML Predictions")
        
        # ============================================================
        # FINAL SUMMARY
        # ============================================================
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 70))
        self.stdout.write(self.style.SUCCESS("✅ LIVE POLYMARKET SEEDING COMPLETE"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(f"  👥 Users: {User.objects.count()}")
        self.stdout.write(f"  📊 Markets: {Market.objects.count()} (LIVE from Polymarket API)")
        self.stdout.write(f"  💰 Trades: {Trade.objects.count()}")
        self.stdout.write(f"  🔒 Security Logs: {SecurityLog.objects.count()}")
        self.stdout.write(f"  🤖 ML Predictions: {TradeRiskPrediction.objects.count()}")
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.WARNING("\n💡 TIP: Install requests if needed:"))
        self.stdout.write("   docker-compose exec web pip install requests")
