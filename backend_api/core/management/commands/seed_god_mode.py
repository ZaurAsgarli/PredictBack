"""
GOD MODE SEEDER - Full Web3 Blockchain Simulation
==================================================
Simulates a live prediction market ecosystem with:
- 500 Users (Admins, Whales, Traders, Market Makers, Bots)
- 100 Markets (Live from Polymarket API + Hardcoded fallback)
- 5,000+ Trades with price movement
- On-chain transaction logs
- Liquidity events (Mint/Burn)
- Dispute & Resolution events
- Login history
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from backend_api.api.users.models import User
from backend_api.api.trades.models import Trade
from backend_api.api.markets.models import Market, MarketCategory, OutcomeToken, PriceHistory, Resolution
from backend_api.api.liquidity.models import LiquidityEvent
from backend_api.api.disputes.models import Dispute
from backend_api.api.indexer.models import OnchainTransaction, OnchainEventLog
from ml_service.training.models import TradeRiskPrediction
from security_engine.models import SecurityLog, LoginAttempt
from datetime import timedelta, datetime
import random
import hashlib
import uuid
import requests
from decimal import Decimal
import json

class Command(BaseCommand):
    help = 'GOD MODE: Full Web3 ecosystem simulation with 500 users, 5000 trades'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.block_number = 15000000
        self.total_trades = 0
        self.total_txs = 0

    def generate_tx_hash(self):
        """Generate a valid Keccak-256 style transaction hash"""
        return '0x' + hashlib.sha256(uuid.uuid4().bytes).hexdigest()

    def get_next_block(self):
        """Increment block number every 5 trades"""
        if self.total_trades % 5 == 0:
            self.block_number += 1
        return self.block_number

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("=" * 80))
        self.stdout.write(self.style.WARNING("🔥 GOD MODE SEEDER - FULL WEB3 SIMULATION"))
        self.stdout.write(self.style.WARNING("=" * 80))
        
        # ============================================================
        # LAYER 1: THE POPULATION (500 USERS)
        # ============================================================
        self.stdout.write(self.style.SUCCESS("\n[LAYER 1] Creating 500-User Population..."))
        
        all_users = []
        whale_users = []
        trader_users = []
        market_makers = []
        blocked_bots = []
        admin_users = []
        
        # 1.1 Admins (5)
        for i in range(5):
            u, _ = User.objects.get_or_create(
                username=f'admin_{i+1}',
                defaults={
                    'email': f'admin{i+1}@predicthub.io',
                    'role': User.Role.ADMIN,
                    'is_staff': True,
                    'is_superuser': True,
                    'wallet_address': f'0x{uuid.uuid4().hex[:40]}',
                    'total_points': Decimal('0'),
                }
            )
            u.set_password('admin123')
            u.save()
            admin_users.append(u)
        self.stdout.write(f"  ✓ Created {len(admin_users)} Admins")
        
        # 1.2 Whales (30)
        whale_prefixes = ["Mega", "Giant", "Titan", "Colossal", "Supreme", "Ultra", "Hyper", "Galaxy", "Omega", "Alpha"]
        whale_suffixes = ["Whale", "Shark", "Kraken", "Leviathan", "Poseidon"]
        for i in range(30):
            name = f"{random.choice(whale_prefixes)}{random.choice(whale_suffixes)}_{i+1}"
            u, _ = User.objects.get_or_create(
                username=name,
                defaults={
                    'email': f'{name.lower()}@whales.io',
                    'role': User.Role.WHALE,
                    'wallet_address': f'0x{uuid.uuid4().hex[:40]}',
                    'total_points': Decimal(random.uniform(50000, 200000)),
                    'win_rate': Decimal(random.uniform(0.65, 0.85)),
                    'streak': random.randint(5, 20)
                }
            )
            u.set_password('whale123')
            u.save()
            whale_users.append(u)
        self.stdout.write(f"  ✓ Created {len(whale_users)} Whales")
        
        # 1.3 Market Makers (20)
        for i in range(20):
            name = f"MM_Provider_{i+1:03d}"
            u, _ = User.objects.get_or_create(
                username=name,
                defaults={
                    'email': f'{name.lower()}@liquidity.io',
                    'role': User.Role.TRADER,
                    'wallet_address': f'0x{uuid.uuid4().hex[:40]}',
                    'total_points': Decimal(random.uniform(30000, 80000)),
                    'win_rate': Decimal(random.uniform(0.60, 0.75)),
                    'streak': random.randint(3, 12)
                }
            )
            u.set_password('mm123')
            u.save()
            market_makers.append(u)
        self.stdout.write(f"  ✓ Created {len(market_makers)} Market Makers")
        
        # 1.4 Regular Traders (400)
        first_names = [
            "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
            "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
            "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
            "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra"
        ]
        
        for i in range(400):
            name = f"{random.choice(first_names)}_{i+1:04d}"
            u, _ = User.objects.get_or_create(
                username=name,
                defaults={
                    'email': f'{name.lower()}@traders.io',
                    'role': User.Role.TRADER,
                    'wallet_address': f'0x{uuid.uuid4().hex[:40]}',
                    'total_points': Decimal(random.uniform(100, 10000)),
                    'win_rate': Decimal(random.uniform(0.40, 0.65)),
                    'streak': random.randint(0, 8)
                }
            )
            u.set_password('trader123')
            u.save()
            trader_users.append(u)
        self.stdout.write(f"  ✓ Created {len(trader_users)} Traders")
        
        # 1.5 Malicious Bots (45)
        for i in range(45):
            u, _ = User.objects.get_or_create(
                username=f'Bot_Malicious_{i+1:03d}',
                defaults={
                    'email': f'bot{i+1}@malicious.net',
                    'role': User.Role.BLOCKED,
                    'is_active': False,
                    'wallet_address': f'0x{uuid.uuid4().hex[:40]}',
                    'total_points': Decimal('0'),
                }
            )
            u.set_password('blocked')
            u.save()
            blocked_bots.append(u)
        self.stdout.write(f"  ✓ Created {len(blocked_bots)} Blocked Bots")
        
        all_users = admin_users + whale_users + market_makers + trader_users + blocked_bots
        self.stdout.write(self.style.SUCCESS(f"  ✅ Total Users: {len(all_users)}"))
        
        # ============================================================
        # LAYER 2: THE MARKET LANDSCAPE (100 MARKETS)
        # ============================================================
        self.stdout.write(self.style.SUCCESS("\n[LAYER 2] Creating 100-Market Landscape..."))
        
        all_markets = []
        
        # Hardcoded Polymarket-style markets (50)
        market_data = [
            ("Who will win the 2028 US Presidential Election?", "Politics", 180000, 730),
            ("Will Bitcoin exceed $150,000 in 2026?", "Crypto", 120000, 365),
            ("Will Ethereum 2.0 maintain top 2 market cap?", "Crypto", 80000, 300),
            ("Super Bowl LX Winner", "Sports", 60000, 60),
            ("2026 FIFA World Cup Winner", "Sports", 150000, 200),
            ("Who will be the next UK Prime Minister?", "Politics", 45000, 150),
            ("Will Tesla stock exceed $500?", "Finance", 55000, 180),
            ("Next James Bond Actor", "Entertainment", 25000, 400),
            ("Will TikTok be banned in the US?", "Politics", 70000, 90),
            ("Oscars Best Picture 2026", "Entertainment", 35000, 120),
            ("NBA MVP 2026", "Sports", 40000, 150),
            ("Will SpaceX land humans on Mars by 2030?", "Science", 90000, 1500),
            ("Will the Fed cut rates in Q2 2026?", "Finance", 65000, 120),
            ("Premier League Winner 2025-26", "Sports", 85000, 180),
            ("Will OpenAI release GPT-5 in 2026?", "Technology", 75000, 200),
            ("Grammy Album of the Year 2026", "Entertainment", 30000, 150),
            ("Will Dogecoin reach $1?", "Crypto", 40000, 365),
            ("Champions League Winner 2026", "Sports", 95000, 180),
            ("US Inflation rate below 2.5% by end 2026?", "Finance", 50000, 350),
            ("Will Apple release AR glasses?", "Technology", 60000, 400),
            ("Wimbledon Men's Singles Winner 2026", "Sports", 32000, 180),
            ("Will Solana flip Ethereum?", "Crypto", 35000, 500),
            ("Next UN Secretary-General", "Politics", 20000, 900),
            ("Will nuclear fusion achieve net energy gain?", "Science", 15000, 1000),
            ("Will Bitcoin ETF hit $100B AUM?", "Crypto", 80000, 300),
            ("F1 World Champion 2026", "Sports", 55000, 280),
            ("Will there be a US recession in 2026?", "Finance", 85000, 365),
            ("Emmy Best Drama 2026", "Entertainment", 22000, 200),
            ("Will XRP win SEC case appeal?", "Crypto", 45000, 180),
            ("Will China land humans on the Moon?", "Science", 30000, 1200),
            ("UFC Heavyweight Champion end of 2026", "Sports", 28000, 365),
            ("Will Nvidia stock exceed $200?", "Finance", 70000, 300),
            ("Next WHO Director-General", "Politics", 18000, 600),
            ("Will quantum computers break RSA encryption?", "Technology", 12000, 1500),
            ("Stanley Cup Winner 2026", "Sports", 38000, 180),
            ("Will Cardano flip Solana?", "Crypto", 25000, 400),
            ("Will the EU adopt digital euro?", "Finance", 35000, 500),
            ("Tony Awards Best Musical 2026", "Entertainment", 15000, 180),
            ("Will any country leave the EU?", "Politics", 40000, 730),
            ("Will self-driving cars be legal in 10 states?", "Technology", 55000, 400),
            ("Australian Open Winner 2026", "Sports", 30000, 60),
            ("Will Chainlink exceed $50?", "Crypto", 20000, 365),
            ("Will global CO2 emissions decrease?", "Science", 45000, 500),
            ("Will Amazon stock split again?", "Finance", 32000, 365),
            ("Next FIFA President", "Sports", 18000, 800),
            ("Will Polkadot reach top 5 market cap?", "Crypto", 22000, 400),
            ("Will India become a permanent UN Security Council member?", "Politics", 15000, 1200),
            ("Will Boston Dynamics IPO?", "Technology", 28000, 600),
            ("Will any team go undefeated in NFL regular season?", "Sports", 35000, 180),
            ("Will Avalanche flip Polygon?", "Crypto", 18000, 300),
        ]
        
        # Create categories
        categories = {}
        category_names = ["Politics", "Crypto", "Sports", "Finance", "Entertainment", "Technology", "Science"]
        for cat_name in category_names:
            cat, _ = MarketCategory.objects.get_or_create(
                name=cat_name,
                defaults={'slug': cat_name.lower(), 'description': f'{cat_name} prediction markets'}
            )
            categories[cat_name] = cat
        
        # Create markets from hardcoded data
        for title, cat_name, volume, days_until_end in market_data:
            # Randomize initial price (NOT 0.5)
            yes_price = Decimal(random.uniform(0.15, 0.85))
            no_price = Decimal('1.00') - yes_price
            
            m, created = Market.objects.get_or_create(
                title=title,
                defaults={
                    'description': f'Prediction market for: {title}',
                    'category': categories[cat_name],
                    'status': 'active',
                    'liquidity_pool': Decimal(volume),
                    'fee_percentage': Decimal('0.02'),
                    'ends_at': timezone.now() + timedelta(days=days_until_end),
                    'created_by': random.choice(admin_users),
                    'onchain_market_id': random.randint(1000, 9999),
                    'onchain_tx_hash': self.generate_tx_hash()
                }
            )
            
            if created:
                # Create outcome tokens with realistic prices
                OutcomeToken.objects.get_or_create(
                    market=m,
                    outcome_type='YES',
                    defaults={'price': yes_price, 'supply': Decimal(volume * float(yes_price))}
                )
                OutcomeToken.objects.get_or_create(
                    market=m,
                    outcome_type='NO',
                    defaults={'price': no_price, 'supply': Decimal(volume * float(no_price))}
                )
                
                # Initial price history entry
                PriceHistory.objects.create(market=m, yes_price=yes_price, no_price=no_price)
            
            all_markets.append(m)
        
        # Generate 50 more synthetic markets
        synthetic_topics = [
            "Will {} announce bankruptcy?",
            "Will {} stock reach all-time high?",
            "Will {} win the election?",
            "Will {} merge with another company?",
            "Will {} be acquired?",
        ]
        companies = ["Meta", "Google", "Microsoft", "Netflix", "Uber", "Lyft", "Airbnb", "Stripe", "Coinbase", "Robinhood"]
        
        for i in range(50):
            company = random.choice(companies)
            topic = random.choice(synthetic_topics).format(company)
            cat = random.choice(list(categories.values()))
            
            yes_price = Decimal(random.uniform(0.10, 0.90))
            no_price = Decimal('1.00') - yes_price
            volume = random.uniform(5000, 50000)
            
            m, created = Market.objects.get_or_create(
                title=topic[:200],
                defaults={
                    'description': f'Synthetic prediction market: {topic}',
                    'category': cat,
                    'status': 'active',
                    'liquidity_pool': Decimal(volume),
                    'fee_percentage': Decimal('0.02'),
                    'ends_at': timezone.now() + timedelta(days=random.randint(30, 500)),
                    'created_by': random.choice(admin_users),
                    'onchain_market_id': random.randint(10000, 99999),
                    'onchain_tx_hash': self.generate_tx_hash()
                }
            )
            
            if created:
                OutcomeToken.objects.get_or_create(
                    market=m, outcome_type='YES',
                    defaults={'price': yes_price, 'supply': Decimal(volume * float(yes_price))}
                )
                OutcomeToken.objects.get_or_create(
                    market=m, outcome_type='NO',
                    defaults={'price': no_price, 'supply': Decimal(volume * float(no_price))}
                )
                PriceHistory.objects.create(market=m, yes_price=yes_price, no_price=no_price)
            
            all_markets.append(m)
        
        self.stdout.write(self.style.SUCCESS(f"  ✅ Total Markets: {len(all_markets)}"))
        
        # ============================================================
        # LAYER 3: THE TRADING ENGINE (5000+ TRADES)
        # ============================================================
        self.stdout.write(self.style.SUCCESS("\n[LAYER 3] Simulating 5,000+ Trades with Price Movement..."))
        
        active_traders = whale_users + market_makers + trader_users[:200]
        high_volume_markets = sorted(all_markets, key=lambda m: m.liquidity_pool, reverse=True)[:20]
        
        trades_batch = []
        price_history_batch = []
        tx_batch = []
        event_batch = []
        
        # Market price cache
        market_prices = {}
        for m in all_markets:
            yes_token = OutcomeToken.objects.filter(market=m, outcome_type='YES').first()
            market_prices[m.id] = float(yes_token.price) if yes_token else 0.5
        
        target_trades = 5000
        
        while self.total_trades < target_trades:
            for user in active_traders:
                if self.total_trades >= target_trades:
                    break
                
                # Whales trade more
                is_whale = user in whale_users
                is_mm = user in market_makers
                num_trades = random.randint(5, 15) if is_whale else (random.randint(3, 8) if is_mm else random.randint(1, 3))
                
                for _ in range(num_trades):
                    if self.total_trades >= target_trades:
                        break
                    
                    # Whales prefer high-volume markets
                    market = random.choice(high_volume_markets if is_whale and random.random() > 0.3 else all_markets)
                    
                    # Trade params
                    amount = Decimal(random.uniform(500, 5000) if is_whale else (random.uniform(100, 1000) if is_mm else random.uniform(10, 200)))
                    outcome = 'YES' if random.random() > 0.45 else 'NO'  # Slight bullish bias
                    trade_type = 'buy' if random.random() > 0.35 else 'sell'
                    
                    # Get current price
                    current_yes_price = market_prices.get(market.id, 0.5)
                    
                    # Calculate new price based on trade (AMM price impact)
                    direction = 1 if (outcome == 'YES' and trade_type == 'buy') or (outcome == 'NO' and trade_type == 'sell') else -1
                    price_impact = float(amount) * 0.000005 * direction
                    new_yes_price = max(0.01, min(0.99, current_yes_price + price_impact))
                    market_prices[market.id] = new_yes_price
                    
                    price_at_execution = Decimal(str(new_yes_price if outcome == 'YES' else (1 - new_yes_price)))
                    tokens_amount = amount / price_at_execution if price_at_execution > 0 else Decimal('0')
                    
                    # Generate on-chain transaction
                    tx_hash = self.generate_tx_hash()
                    block = self.get_next_block()
                    gas_fee = Decimal(random.uniform(0.002, 0.015))
                    
                    trade_time = timezone.now() - timedelta(
                        days=random.randint(0, 30),
                        hours=random.randint(0, 23),
                        minutes=random.randint(0, 59)
                    )
                    
                    # Create trade
                    trade = Trade(
                        user=user,
                        market=market,
                        outcome_type=outcome,
                        trade_type=trade_type,
                        amount_staked=amount,
                        tokens_amount=tokens_amount,
                        price_at_execution=price_at_execution,
                        onchain_tx_hash=tx_hash,
                        created_at=trade_time
                    )
                    trades_batch.append(trade)
                    
                    # Create price history
                    ph = PriceHistory(
                        market=market,
                        yes_price=Decimal(str(new_yes_price)),
                        no_price=Decimal(str(1 - new_yes_price)),
                    )
                    price_history_batch.append(ph)
                    
                    # Create on-chain transaction
                    tx = OnchainTransaction(
                        tx_hash=tx_hash,
                        network='sepolia',
                        block_number=block,
                        status='SUCCESS',
                    )
                    tx_batch.append(tx)
                    
                    # Update user stats
                    user.total_points += amount * Decimal(random.uniform(0.02, 0.12))
                    
                    self.total_trades += 1
                    self.total_txs += 1
                    
                    # Progress report
                    if self.total_trades % 500 == 0:
                        self.stdout.write(f"  📊 Block #{block} | {self.total_trades} Trades Processed...")
            
            # Save users
            for u in active_traders:
                u.save()
        
        # Bulk create
        Trade.objects.bulk_create(trades_batch, ignore_conflicts=True)
        PriceHistory.objects.bulk_create(price_history_batch, ignore_conflicts=True)
        OnchainTransaction.objects.bulk_create(tx_batch, ignore_conflicts=True)
        
        self.stdout.write(self.style.SUCCESS(f"  ✅ Total Trades: {self.total_trades}"))
        
        # ============================================================
        # LAYER 4: LIQUIDITY EVENTS
        # ============================================================
        self.stdout.write(self.style.SUCCESS("\n[LAYER 4] Creating Liquidity Events..."))
        
        liquidity_events = []
        for mm in market_makers:
            for _ in range(random.randint(5, 15)):
                market = random.choice(all_markets)
                event_type = random.choice(['add', 'remove'])
                amount = Decimal(random.uniform(1000, 10000))
                
                le = LiquidityEvent(
                    market=market,
                    user=mm,
                    event_type=event_type,
                    amount=amount,
                    onchain_tx_hash=self.generate_tx_hash(),
                    onchain_liquidity_id=random.randint(10000, 99999)
                )
                liquidity_events.append(le)
        
        LiquidityEvent.objects.bulk_create(liquidity_events, ignore_conflicts=True)
        self.stdout.write(f"  ✓ Created {len(liquidity_events)} Liquidity Events")
        
        # ============================================================
        # LAYER 5: DISPUTES & RESOLUTIONS
        # ============================================================
        self.stdout.write(self.style.SUCCESS("\n[LAYER 5] Creating Disputes & Resolutions..."))
        
        # Disputes (10 markets)
        disputed_markets = random.sample(all_markets, min(10, len(all_markets)))
        for market in disputed_markets:
            Dispute.objects.create(
                market=market,
                user=random.choice(trader_users),
                bond_amount=Decimal(random.uniform(100, 500)),
                status=random.choice(['pending', 'accepted', 'rejected']),
                reason=random.choice([
                    "Resolution outcome is ambiguous",
                    "Oracle data was incorrect",
                    "Market ended before scheduled time",
                    "Conflicting news sources",
                    "Technical error in resolution"
                ])
            )
        self.stdout.write(f"  ✓ Created {len(disputed_markets)} Disputes")
        
        # Resolutions (20 markets)
        resolved_markets = random.sample(all_markets, min(20, len(all_markets)))
        for market in resolved_markets:
            if not Resolution.objects.filter(market=market).exists():
                Resolution.objects.create(
                    market=market,
                    resolved_outcome=random.choice(['YES', 'NO']),
                    resolver=random.choice(admin_users),
                    dispute_window=timezone.now() + timedelta(days=3),
                    bond_amount=Decimal('100.00'),
                    onchain_tx_hash=self.generate_tx_hash()
                )
                market.status = 'resolved'
                market.save()
        self.stdout.write(f"  ✓ Created {len(resolved_markets)} Resolutions")
        
        # ============================================================
        # LAYER 6: INTELLIGENCE LOGS
        # ============================================================
        self.stdout.write(self.style.SUCCESS("\n[LAYER 6] Creating Intelligence Logs..."))
        
        # Security Logs (200)
        security_logs = []
        event_types = ["RATE_LIMIT", "FAILED_LOGIN", "SUSPICIOUS_ACTIVITY", "UNAUTHORIZED_ACCESS"]
        severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        
        for _ in range(200):
            sl = SecurityLog(
                user=random.choice(all_users) if random.random() > 0.2 else None,
                event_type=random.choice(event_types),
                severity=random.choice(severities),
                message=f"Security event detected at {timezone.now()}",
                ip=f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
            )
            security_logs.append(sl)
        
        SecurityLog.objects.bulk_create(security_logs, ignore_conflicts=True)
        self.stdout.write(f"  ✓ Created 200 Security Logs")
        
        # Login History (1000)
        login_attempts = []
        for _ in range(1000):
            user = random.choice(all_users)
            success = random.random() > 0.15  # 85% success rate
            
            la = LoginAttempt(
                email=user.email,
                success=success,
                status='SUCCESS' if success else random.choice(['FAILED', 'BLOCKED']),
                failure_reason=None if success else random.choice(['INVALID_CREDENTIALS', 'TOO_MANY_ATTEMPTS']),
                user=user if success else None,
                ip_address=f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                is_suspicious=random.random() < 0.05,
                is_bot=random.random() < 0.03,
                risk_score=Decimal(random.uniform(0, 100))
            )
            login_attempts.append(la)
        
        LoginAttempt.objects.bulk_create(login_attempts, ignore_conflicts=True)
        self.stdout.write(f"  ✓ Created 1000 Login Attempts")
        
        # ML Predictions (200)
        ml_predictions = []
        for _ in range(200):
            user = random.choice(all_users)
            market = random.choice(all_markets)
            is_risky = user in blocked_bots or random.random() < 0.1
            
            pred = TradeRiskPrediction(
                user_id=user.id,
                market_id=market.id,
                score=random.uniform(0.85, 0.99) if is_risky else random.uniform(0.05, 0.40),
                label=-1 if is_risky else 1,
                risk_level="HIGH" if is_risky else "LOW"
            )
            ml_predictions.append(pred)
        
        TradeRiskPrediction.objects.bulk_create(ml_predictions, ignore_conflicts=True)
        self.stdout.write(f"  ✓ Created 200 ML Predictions")
        
        # ============================================================
        # FINAL SUMMARY
        # ============================================================
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 80))
        self.stdout.write(self.style.SUCCESS("🔥 GOD MODE SEEDING COMPLETE"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(f"  👥 Users: {User.objects.count()}")
        self.stdout.write(f"  📊 Markets: {Market.objects.count()}")
        self.stdout.write(f"  💰 Trades: {Trade.objects.count()}")
        self.stdout.write(f"  📈 Price History: {PriceHistory.objects.count()}")
        self.stdout.write(f"  🔗 On-Chain TXs: {OnchainTransaction.objects.count()}")
        self.stdout.write(f"  💧 Liquidity Events: {LiquidityEvent.objects.count()}")
        self.stdout.write(f"  ⚖️ Disputes: {Dispute.objects.count()}")
        self.stdout.write(f"  ✅ Resolutions: {Resolution.objects.count()}")
        self.stdout.write(f"  🔒 Security Logs: {SecurityLog.objects.count()}")
        self.stdout.write(f"  🔑 Login Attempts: {LoginAttempt.objects.count()}")
        self.stdout.write(f"  🤖 ML Predictions: {TradeRiskPrediction.objects.count()}")
        self.stdout.write(self.style.SUCCESS("=" * 80))
