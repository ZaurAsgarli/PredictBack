"""
Django management command to seed example data for all models.
Run with: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random
import secrets

from users.models import User
from markets.models import Market, MarketCategory, OutcomeToken, PriceHistory, Resolution
from trades.models import Trade
from positions.models import Position
from liquidity.models import LiquidityEvent
from disputes.models import Dispute
from indexer.models import OnchainTransaction, OnchainEventLog


class Command(BaseCommand):
    help = 'Seeds the database with example data for all models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            # Clear in reverse dependency order
            OnchainEventLog.objects.all().delete()
            OnchainTransaction.objects.all().delete()
            Dispute.objects.all().delete()
            Resolution.objects.all().delete()
            PriceHistory.objects.all().delete()
            Trade.objects.all().delete()
            Position.objects.all().delete()
            LiquidityEvent.objects.all().delete()
            OutcomeToken.objects.all().delete()
            Market.objects.all().delete()
            MarketCategory.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared.'))

        self.stdout.write(self.style.SUCCESS('Starting seed process...'))

        # 1. Create Market Categories (3-4 examples)
        categories_data = [
            {
                'name': 'Sports',
                'slug': 'sports',
                'description': 'Sports and athletic competitions predictions'
            },
            {
                'name': 'Politics',
                'slug': 'politics',
                'description': 'Political events, elections, and policy predictions'
            },
            {
                'name': 'Technology',
                'slug': 'technology',
                'description': 'Tech industry, product launches, and innovation predictions'
            },
            {
                'name': 'Entertainment',
                'slug': 'entertainment',
                'description': 'Movies, TV shows, music, and celebrity predictions'
            },
        ]

        categories = {}
        for cat_data in categories_data:
            category, created = MarketCategory.objects.get_or_create(
                slug=cat_data['slug'],
                defaults=cat_data
            )
            categories[cat_data['slug']] = category
            self.stdout.write(f"  {'✓ Created' if created else '→ Found'} category: {category.name}")

        # 2. Create Users (3-4 examples)
        users_data = [
            {
                'username': 'alice_trader',
                'email': 'alice@example.com',
                'total_points': Decimal('1250.50'),
                'win_rate': Decimal('68.5'),
                'streak': 5,
                'role': 'user'
            },
            {
                'username': 'bob_predictor',
                'email': 'bob@example.com',
                'total_points': Decimal('890.25'),
                'win_rate': Decimal('55.2'),
                'streak': 2,
                'role': 'user'
            },
            {
                'username': 'charlie_market',
                'email': 'charlie@example.com',
                'total_points': Decimal('2100.75'),
                'win_rate': Decimal('72.8'),
                'streak': 8,
                'role': 'user'
            },
            {
                'username': 'diana_admin',
                'email': 'diana@example.com',
                'total_points': Decimal('500.00'),
                'win_rate': Decimal('45.0'),
                'streak': 0,
                'role': 'admin'
            },
        ]

        users = []
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                email=user_data['email'],
                defaults={
                    'username': user_data['username'],
                    'total_points': user_data['total_points'],
                    'win_rate': user_data['win_rate'],
                    'streak': user_data['streak'],
                    'role': user_data['role'],
                }
            )
            if created:
                user.set_password('password123')
                user.save()
            users.append(user)
            self.stdout.write(f"  {'✓ Created' if created else '→ Found'} user: {user.username} ({user.email})")

        # 3. Create Markets (3-4 examples)
        markets_data = [
            {
                'title': 'Will the Lakers win the NBA Championship in 2024?',
                'description': 'Prediction on whether the Los Angeles Lakers will win the NBA Championship in the 2024 season. This includes all playoff rounds and the finals.',
                'category': categories['sports'],
                'status': 'active',
                'liquidity_pool': Decimal('5000.00'),
                'ends_at': timezone.now() + timedelta(days=60),
                'created_by': users[0],
            },
            {
                'title': 'Will Bitcoin reach $100,000 by end of 2024?',
                'description': 'Prediction on whether Bitcoin (BTC) will reach or exceed $100,000 USD by December 31, 2024. Price must be sustained for at least 24 hours.',
                'category': categories['technology'],
                'status': 'active',
                'liquidity_pool': Decimal('12000.00'),
                'ends_at': timezone.now() + timedelta(days=120),
                'created_by': users[1],
            },
            {
                'title': 'Will the new Marvel movie gross over $500M worldwide?',
                'description': 'Prediction on whether the upcoming Marvel Studios movie will gross over $500 million USD in worldwide box office revenue within its first 3 months of release.',
                'category': categories['entertainment'],
                'status': 'active',
                'liquidity_pool': Decimal('8000.00'),
                'ends_at': timezone.now() + timedelta(days=90),
                'created_by': users[2],
            },
            {
                'title': 'Will there be a major policy change announced before Q2 2024?',
                'description': 'Prediction on whether a major government policy change will be officially announced before the end of Q2 2024. Must be confirmed by official government sources.',
                'category': categories['politics'],
                'status': 'resolved',
                'liquidity_pool': Decimal('3000.00'),
                'resolution_outcome': 'YES',
                'ends_at': timezone.now() - timedelta(days=10),
                'created_by': users[0],
            },
        ]

        markets = []
        for i, market_data in enumerate(markets_data):
            market = Market.objects.create(
                **market_data,
                fee_percentage=Decimal('0.02'),
                onchain_market_id=i + 1,
                onchain_tx_hash=f"0x{secrets.token_hex(32)}" if i < 2 else None,
            )

            # Create outcome tokens for each market
            yes_supply = market.liquidity_pool / Decimal('2')
            no_supply = market.liquidity_pool / Decimal('2')
            
            OutcomeToken.objects.create(
                market=market,
                outcome_type='YES',
                supply=yes_supply,
                price=Decimal('0.5')
            )
            OutcomeToken.objects.create(
                market=market,
                outcome_type='NO',
                supply=no_supply,
                price=Decimal('0.5')
            )

            # Create initial price history
            PriceHistory.objects.create(
                market=market,
                yes_price=Decimal('0.5'),
                no_price=Decimal('0.5')
            )

            markets.append(market)
            self.stdout.write(f"  ✓ Created market: {market.title}")

        # 4. Create Trades (3-4 examples)
        trades_data = [
            {
                'user': users[0],
                'market': markets[0],
                'outcome_type': 'YES',
                'trade_type': 'buy',
                'amount_staked': Decimal('100.00'),
                'tokens_amount': Decimal('200.00'),
                'price_at_execution': Decimal('0.50'),
                'onchain_tx_hash': f"0x{secrets.token_hex(32)}",
                'onchain_trade_id': 1,
            },
            {
                'user': users[1],
                'market': markets[0],
                'outcome_type': 'NO',
                'trade_type': 'buy',
                'amount_staked': Decimal('150.00'),
                'tokens_amount': Decimal('300.00'),
                'price_at_execution': Decimal('0.50'),
                'onchain_tx_hash': f"0x{secrets.token_hex(32)}",
                'onchain_trade_id': 2,
            },
            {
                'user': users[2],
                'market': markets[1],
                'outcome_type': 'YES',
                'trade_type': 'buy',
                'amount_staked': Decimal('250.00'),
                'tokens_amount': Decimal('500.00'),
                'price_at_execution': Decimal('0.50'),
                'onchain_tx_hash': f"0x{secrets.token_hex(32)}",
                'onchain_trade_id': 3,
            },
            {
                'user': users[0],
                'market': markets[2],
                'outcome_type': 'YES',
                'trade_type': 'sell',
                'amount_staked': Decimal('75.00'),
                'tokens_amount': Decimal('150.00'),
                'price_at_execution': Decimal('0.50'),
                'onchain_tx_hash': f"0x{secrets.token_hex(32)}",
                'onchain_trade_id': 4,
            },
        ]

        for trade_data in trades_data:
            trade = Trade.objects.create(**trade_data)
            self.stdout.write(f"  ✓ Created trade: {trade.user.username} - {trade.trade_type} {trade.outcome_type} on {trade.market.title[:30]}...")

        # 5. Create Positions (3-4 examples)
        positions_data = [
            {
                'user': users[0],
                'market': markets[0],
                'yes_tokens': Decimal('200.00'),
                'no_tokens': Decimal('0.00'),
                'total_staked': Decimal('100.00'),
            },
            {
                'user': users[1],
                'market': markets[0],
                'yes_tokens': Decimal('0.00'),
                'no_tokens': Decimal('300.00'),
                'total_staked': Decimal('150.00'),
            },
            {
                'user': users[2],
                'market': markets[1],
                'yes_tokens': Decimal('500.00'),
                'no_tokens': Decimal('0.00'),
                'total_staked': Decimal('250.00'),
            },
            {
                'user': users[0],
                'market': markets[2],
                'yes_tokens': Decimal('50.00'),
                'no_tokens': Decimal('0.00'),
                'total_staked': Decimal('25.00'),
            },
        ]

        for position_data in positions_data:
            position, created = Position.objects.get_or_create(
                user=position_data['user'],
                market=position_data['market'],
                defaults=position_data
            )
            if not created:
                position.yes_tokens = position_data['yes_tokens']
                position.no_tokens = position_data['no_tokens']
                position.total_staked = position_data['total_staked']
                position.save()
            self.stdout.write(f"  {'✓ Created' if created else '→ Updated'} position: {position.user.username} - {position.market.title[:30]}...")

        # 6. Create Liquidity Events (3-4 examples)
        liquidity_events_data = [
            {
                'market': markets[0],
                'user': users[0],
                'event_type': 'add',
                'amount': Decimal('1000.00'),
                'onchain_tx_hash': f"0x{secrets.token_hex(32)}",
                'onchain_liquidity_id': 1,
            },
            {
                'market': markets[1],
                'user': users[1],
                'event_type': 'add',
                'amount': Decimal('2000.00'),
                'onchain_tx_hash': f"0x{secrets.token_hex(32)}",
                'onchain_liquidity_id': 2,
            },
            {
                'market': markets[2],
                'user': users[2],
                'event_type': 'add',
                'amount': Decimal('1500.00'),
                'onchain_tx_hash': f"0x{secrets.token_hex(32)}",
                'onchain_liquidity_id': 3,
            },
            {
                'market': markets[0],
                'user': users[0],
                'event_type': 'remove',
                'amount': Decimal('200.00'),
                'onchain_tx_hash': f"0x{secrets.token_hex(32)}",
                'onchain_liquidity_id': 4,
            },
        ]

        for event_data in liquidity_events_data:
            event = LiquidityEvent.objects.create(**event_data)
            self.stdout.write(f"  ✓ Created liquidity event: {event.event_type} {event.amount} by {event.user.username}")

        # 7. Create Disputes (2-3 examples)
        disputes_data = [
            {
                'market': markets[3],  # Resolved market
                'user': users[1],
                'bond_amount': Decimal('100.00'),
                'status': 'pending',
                'reason': 'I believe the resolution was incorrect. The policy change was not officially announced as required by the market rules.',
            },
            {
                'market': markets[3],
                'user': users[2],
                'bond_amount': Decimal('150.00'),
                'status': 'accepted',
                'reason': 'The resolution criteria were not met. The announcement was made by a spokesperson, not an official government source.',
                'resolved_at': timezone.now() - timedelta(days=2),
            },
        ]

        for dispute_data in disputes_data:
            dispute = Dispute.objects.create(**dispute_data)
            self.stdout.write(f"  ✓ Created dispute: {dispute.user.username} - {dispute.status}")

        # 8. Create Resolution (1-2 examples)
        resolution = Resolution.objects.create(
            market=markets[3],
            resolved_outcome='YES',
            resolver=users[0],
            dispute_window=timezone.now() + timedelta(days=7),
            bond_amount=Decimal('100.00'),
            onchain_tx_hash=f"0x{secrets.token_hex(32)}",
        )
        self.stdout.write(f"  ✓ Created resolution: {resolution.market.title[:30]}... - {resolution.resolved_outcome}")

        # 9. Create Onchain Transactions (2-3 examples)
        onchain_txs_data = [
            {
                'tx_hash': f"0x{secrets.token_hex(32)}",
                'network': 'sepolia',
                'block_number': 5000000 + random.randint(1, 10000),
                'status': 'SUCCESS',
            },
            {
                'tx_hash': f"0x{secrets.token_hex(32)}",
                'network': 'sepolia',
                'block_number': 5000000 + random.randint(1, 10000),
                'status': 'SUCCESS',
            },
            {
                'tx_hash': f"0x{secrets.token_hex(32)}",
                'network': 'sepolia',
                'block_number': 5000000 + random.randint(1, 10000),
                'status': 'PENDING',
            },
        ]

        onchain_txs = []
        for tx_data in onchain_txs_data:
            tx = OnchainTransaction.objects.create(**tx_data)
            onchain_txs.append(tx)
            self.stdout.write(f"  ✓ Created onchain transaction: {tx.tx_hash[:20]}... ({tx.status})")

        # 10. Create Onchain Event Logs (2-3 examples)
        event_logs_data = [
            {
                'onchain_tx': onchain_txs[0],
                'event_name': 'MarketCreated',
                'tx_hash': onchain_txs[0].tx_hash,
                'log_index': 0,
                'market': markets[0],
                'user_address': f"0x{secrets.token_hex(20)}",
                'payload_json': {
                    'marketId': 1,
                    'creator': f"0x{secrets.token_hex(20)}",
                    'endTime': int((timezone.now() + timedelta(days=60)).timestamp()),
                },
                'processed_at': timezone.now() - timedelta(hours=2),
                'duplicate': False,
            },
            {
                'onchain_tx': onchain_txs[1],
                'event_name': 'TradeExecuted',
                'tx_hash': onchain_txs[1].tx_hash,
                'log_index': 0,
                'market': markets[0],
                'user_address': f"0x{secrets.token_hex(20)}",
                'payload_json': {
                    'marketId': 1,
                    'user': f"0x{secrets.token_hex(20)}",
                    'outcome': True,
                    'amount': '100000000000000000000',  # 100 tokens in wei
                    'tradeId': 1,
                },
                'processed_at': timezone.now() - timedelta(hours=1),
                'duplicate': False,
            },
            {
                'onchain_tx': onchain_txs[2],
                'event_name': 'LiquidityAdded',
                'tx_hash': onchain_txs[2].tx_hash,
                'log_index': 0,
                'market': markets[1],
                'user_address': f"0x{secrets.token_hex(20)}",
                'payload_json': {
                    'marketId': 2,
                    'user': f"0x{secrets.token_hex(20)}",
                    'amount': '2000000000000000000000',  # 2000 tokens in wei
                    'liquidityId': 2,
                },
                'processed_at': None,
                'duplicate': False,
            },
        ]

        for log_data in event_logs_data:
            log = OnchainEventLog.objects.create(**log_data)
            self.stdout.write(f"  ✓ Created event log: {log.event_name} - {log.tx_hash[:20]}...")

        # 11. Create additional Price History entries for charts
        for market in markets[:3]:  # For first 3 markets
            for i in range(5):
                price_variation = Decimal(str(0.45 + random.random() * 0.1))  # Between 0.45 and 0.55
                PriceHistory.objects.create(
                    market=market,
                    yes_price=price_variation,
                    no_price=Decimal('1.0') - price_variation,
                    timestamp=timezone.now() - timedelta(hours=5-i)
                )
            self.stdout.write(f"  ✓ Created price history for: {market.title[:30]}...")

        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('Seed process completed successfully!'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(f"  Market Categories: {MarketCategory.objects.count()}")
        self.stdout.write(f"  Users: {User.objects.count()}")
        self.stdout.write(f"  Markets: {Market.objects.count()}")
        self.stdout.write(f"  Outcome Tokens: {OutcomeToken.objects.count()}")
        self.stdout.write(f"  Trades: {Trade.objects.count()}")
        self.stdout.write(f"  Positions: {Position.objects.count()}")
        self.stdout.write(f"  Liquidity Events: {LiquidityEvent.objects.count()}")
        self.stdout.write(f"  Disputes: {Dispute.objects.count()}")
        self.stdout.write(f"  Resolutions: {Resolution.objects.count()}")
        self.stdout.write(f"  Price History: {PriceHistory.objects.count()}")
        self.stdout.write(f"  Onchain Transactions: {OnchainTransaction.objects.count()}")
        self.stdout.write(f"  Onchain Event Logs: {OnchainEventLog.objects.count()}")
        self.stdout.write(self.style.SUCCESS('\nYou can now view all data in the Django admin panel!'))
        self.stdout.write(self.style.SUCCESS('Admin URL: http://localhost:8000/admin/'))

