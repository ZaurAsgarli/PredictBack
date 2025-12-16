from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import random
import datetime
from faker import Faker
import secrets
from backend_api.api.markets.models import Market, MarketCategory, PriceHistory, Resolution, OutcomeToken
from backend_api.api.trades.models import Trade
from backend_api.api.positions.models import Position
from backend_api.api.disputes.models import Dispute
from backend_api.api.liquidity.models import LiquidityEvent
from security_engine.models import SecurityLog

# Initialize Faker
fake = Faker()

class Command(BaseCommand):
    help = 'Populates the database with massive, realistic data (SDF2 V2).'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('--- STARTING ULTIMATE SEED V2 (SDF2) ---'))
        start_time = timezone.now()

        # 1. SMART WIPE
        self.smart_wipe()

        # 2. SEED CONSTANTS
        self.CATEGORIES = [
            'Crypto', 'Politics', 'Football', 'MMA', 'Tech', 'Business', 
            'Pop Culture', 'Science', 'Geopolitics', 'Climate', 'AI', 'Gaming'
        ]
        
        # 3. GENERATE DATA
        users = self.create_users(count=300)
        markets = self.create_categories_and_markets(count=80) # Increased count
        self.create_trading_history(users, markets)

        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        self.stdout.write(self.style.SUCCESS(f'--- ULTIMATE SEED V2 COMPLETE in {duration:.2f}s ---'))

    def smart_wipe(self):
        """Wipes data but preserves Polymarket (Trending) markets."""
        self.stdout.write('Performing Smart Wipe (V2)...')
        
        # Delete dependent operational data
        LiquidityEvent.objects.all().delete()
        Dispute.objects.all().delete()
        Position.objects.all().delete()
        Trade.objects.all().delete()
        SecurityLog.objects.all().delete()
        PriceHistory.objects.all().delete()
        Resolution.objects.all().delete()
        OutcomeToken.objects.all().delete()
        
        # Delete Users (except superusers/staff)
        get_user_model().objects.filter(is_superuser=False, is_staff=False).delete()
        
        # Delete Markets EXCEPT "Trending"
        deleted_markets, _ = Market.objects.exclude(category__slug='trending').delete()
        self.stdout.write(f' - Deleted {deleted_markets} non-Polymarket markets.')

    def create_users(self, count):
        self.stdout.write(f'Creating {count} Users...')
        users = []
        
        # Nationality distribution
        count_az = int(count * 0.40)
        count_tr = int(count * 0.20)
        count_kr = int(count * 0.20)
        count_en = count - (count_az + count_tr + count_kr)
        
        configs = [
            ('az_AZ', count_az, '_az'),
            ('tr_TR', count_tr, '_tr'),
            ('ko_KR', count_kr, '_kr'),
            ('en_US', count_en, '_en')
        ]
        
        for locale, limit, suffix in configs:
            local_faker = Faker(locale)
            for _ in range(limit):
                try:
                    first_name = local_faker.first_name()
                    last_name = local_faker.last_name()
                    username = f"{first_name.lower()}_{last_name.lower()}{suffix}_{random.randint(10, 999)}"
                    username = username.encode('ascii', 'ignore').decode() or f"user{suffix}_{random.randint(1000,9999)}"
                    
                    email = f"{username}@example.com"
                    is_vip = random.random() < 0.10
                    points = random.randint(50000, 1000000) if is_vip else random.randint(1000, 50000)
                    role = 'vip' if is_vip else 'trader'
                    wallet = f"0x{secrets.token_hex(20)}"
                    
                    user = get_user_model()(
                        username=username,
                        email=email,
                        total_points=points,
                        wallet_address=wallet,
                        role=role,
                        is_active=True
                    )
                    user.set_password('pass123')
                    users.append(user)
                except Exception:
                    continue
        
        get_user_model().objects.bulk_create(users, ignore_conflicts=True)
        self.stdout.write(f' - {len(users)} users processed.')
        return list(get_user_model().objects.all())

    def create_categories_and_markets(self, count):
        self.stdout.write('Creating Categories & Markets...')
        
        cats = []
        for name in self.CATEGORIES:
            slug = name.lower().replace(" ", "-")
            cat, _ = MarketCategory.objects.get_or_create(name=name, defaults={'slug': slug})
            cats.append(cat)
            
        markets = []
        LiquidityEvents = []
        admin_user = get_user_model().objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = get_user_model().objects.first()

        cutoff_date = timezone.now() + datetime.timedelta(days=30)
        
        for _ in range(count):
            cat = random.choice(cats)
            is_resolved = random.random() < 0.30
            status = 'active'
            if is_resolved: status = 'resolved'
            
            title = fake.sentence(nb_words=6).replace(".", "?")
            liq_pool = Decimal(random.randint(1000, 50000))
            
            market = Market(
                title=title,
                description=fake.text(max_nb_chars=200),
                category=cat,
                status=status,
                liquidity_pool=liq_pool,
                created_by=admin_user,
                ends_at=cutoff_date,
                resolution_outcome='YES' if is_resolved and random.choice([True, False]) else None
            )
            markets.append(market)
            
        Market.objects.bulk_create(markets, ignore_conflicts=True)
        all_markets = list(Market.objects.all())
        
        # New: Generate Liquidity Events for every market
        for m in all_markets:
             LiquidityEvents.append(LiquidityEvent(
                 market=m,
                 user=admin_user,
                 event_type='add',
                 amount=m.liquidity_pool if m.liquidity_pool else Decimal('100.00'),
                 onchain_tx_hash=f"0x{secrets.token_hex(32)}",
                 onchain_liquidity_id=random.randint(1, 999999)
             ))
             
             # Outcome tokens
             OutcomeToken.objects.get_or_create(market=m, outcome_type='YES', defaults={'price': 0.5, 'supply': 1000})
             OutcomeToken.objects.get_or_create(market=m, outcome_type='NO', defaults={'price': 0.5, 'supply': 1000})
             
             if m.status == 'resolved' and m.resolution_outcome:
                 Resolution.objects.get_or_create(
                     market=m,
                     defaults={
                         'resolved_outcome': m.resolution_outcome,
                         'resolver': admin_user,
                         'bond_amount': Decimal('100.00'),
                         'dispute_window': timezone.now() + datetime.timedelta(days=7)
                     }
                 )

        LiquidityEvent.objects.bulk_create(LiquidityEvents, ignore_conflicts=True)
        self.stdout.write(f' - {len(markets)} markets & liquidity events created.')
        
        # Create Disputes
        dispute_candidates = [m for m in all_markets if m.status == 'active']
        if dispute_candidates:
            disputes = []
            for m in random.sample(dispute_candidates, min(len(dispute_candidates), int(len(markets) * 0.1))):
                user = random.choice(get_user_model().objects.all())
                disputes.append(Dispute(
                    market=m,
                    user=user,
                    bond_amount=Decimal('50.00'),
                    reason="Oracle malfunction or ambiguous result",
                    status='pending'
                ))
            Dispute.objects.bulk_create(disputes, ignore_conflicts=True)
            self.stdout.write(f' - {len(disputes)} disputes created.')
        
        return all_markets

    def create_trading_history(self, users, markets):
        self.stdout.write('Generating High-Fidelity Trading History...')
        
        trades = []
        price_history = []
        pos_tracker = {}
        
        start_date = timezone.now() - datetime.timedelta(days=30)
        active_users = random.sample(users, min(len(users), 200))
        total_trades = 4000 # Increased
        
        for i in range(total_trades):
            user = random.choice(active_users)
            market = random.choice(markets)
            
            outcome = random.choice(['YES', 'NO'])
            trade_type = random.choice(['buy', 'sell'])
            
            amount = Decimal(random.randint(10, 500))
            if user.role == 'vip': amount *= 5
            
            price = 0.50 + (random.random() - 0.5) * 0.4 
            price = max(0.01, min(0.99, price))
            tokens = amount / Decimal(price)
            
            trade = Trade(
                user=user,
                market=market,
                outcome_type=outcome,
                trade_type=trade_type,
                amount_staked=amount,
                tokens_amount=tokens,
                price_at_execution=Decimal(price),
                created_at=start_date + datetime.timedelta(days=random.randint(0, 30), hours=random.randint(0,23))
            )
            trades.append(trade)
            
            # Position Logic
            if (user.id, market.id) not in pos_tracker:
                pos_tracker[(user.id, market.id)] = {'yes': Decimal(0), 'no': Decimal(0), 'staked': Decimal(0)}
            entry = pos_tracker[(user.id, market.id)]
            
            if trade_type == 'buy':
                entry['staked'] += amount
                if outcome == 'YES': entry['yes'] += tokens
                else: entry['no'] += tokens
            else:
                if outcome == 'YES': entry['yes'] = max(Decimal(0), entry['yes'] - tokens)
                else: entry['no'] = max(Decimal(0), entry['no'] - tokens)
            
            # Price History
            if i % 10 == 0:
                price_history.append(PriceHistory(
                    market=market,
                    yes_price=Decimal(price),
                    no_price=Decimal(1.0 - price),
                    timestamp=trade.created_at
                ))
        
        Trade.objects.bulk_create(trades, ignore_conflicts=True)
        PriceHistory.objects.bulk_create(price_history, ignore_conflicts=True)
        
        positions = []
        for (uid, mid), data in pos_tracker.items():
            if data['yes'] > 0 or data['no'] > 0:
                positions.append(Position(
                    user_id=uid,
                    market_id=mid,
                    yes_tokens=data['yes'],
                    no_tokens=data['no'],
                    total_staked=data['staked']
                ))
        Position.objects.bulk_create(positions, ignore_conflicts=True)
        
        # Security Logs
        logs = []
        for _ in range(500): # Increased
             logs.append(SecurityLog(
                 user=random.choice(users),
                 event_type=random.choice(['LOGIN_FAIL', 'SQL_INJECTION', 'DDOS_ATTEMPT', 'UNUSUAL_GEO', 'RATE_LIMIT']),
                 severity=random.choice(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']),
                 ip=fake.ipv4(),
                 message=fake.sentence(),
                 path='/api/login'
             ))
        SecurityLog.objects.bulk_create(logs, ignore_conflicts=True)
        self.stdout.write(f' - {len(trades)} trades, {len(positions)} positions, {len(logs)} security logs created.')
