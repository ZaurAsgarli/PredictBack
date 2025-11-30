"""
Django management command to reset and seed comprehensive synthetic data for ML experiments.
This command:
1. Cleans all existing synthetic data across ALL related tables
2. Creates fresh, rich synthetic dataset covering Users, Markets, Trades, Positions,
   OutcomeTokens, LiquidityEvents, Resolutions, Disputes, PriceHistory, and Onchain data

Run with: python manage.py reset_and_seed_full_synthetic_data
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum, Q
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
import random
import json

from trades.models import Trade
from markets.models import Market, MarketCategory, PriceHistory, OutcomeToken, Resolution
from positions.models import Position
from liquidity.models import LiquidityEvent
from disputes.models import Dispute

User = get_user_model()

# Try to import onchain models (might not exist)
try:
    from indexer.models import OnchainTransaction, OnchainEventLog
    HAS_ONCHAIN_MODELS = True
except ImportError:
    HAS_ONCHAIN_MODELS = False


class Command(BaseCommand):
    help = 'Resets and seeds comprehensive synthetic data: cleans old data, creates rich dataset across all tables'

    def add_arguments(self, parser):
        parser.add_argument(
            '--seed',
            type=int,
            default=42,
            help='Random seed for deterministic data generation (default: 42)',
        )

    def handle(self, *args, **options):
        random.seed(options['seed'])
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('RESET AND SEED FULL SYNTHETIC DATA FOR ML EXPERIMENTS'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        # STEP 1: Cleanup
        self.stdout.write('\n[STEP 1] Cleaning existing synthetic data...')
        self._cleanup_synthetic_data()
        
        # STEP 2: Re-seed
        self.stdout.write('\n[STEP 2] Creating fresh synthetic dataset...')
        
        # Get or create synthetic category
        try:
            category, _ = MarketCategory.objects.get_or_create(
                slug='synthetic',
                defaults={
                    'name': 'Synthetic',
                    'description': 'Synthetic category for ML/testing'
                }
            )
            self.stdout.write(f"✓ Using category: {category.name}")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠ Category creation skipped: {e}"))
            category = None
        
        # Create users
        self.stdout.write('\n[2.1] Creating synthetic users...')
        synthetic_users, user_types = self._create_synthetic_users()
        self.stdout.write(f"✓ Created {len(synthetic_users)} synthetic users")
        self.stdout.write(f"  - Passive users (15%): {user_types['passive']}")
        self.stdout.write(f"  - Normal users (70%): {user_types['normal']}")
        self.stdout.write(f"  - CRAZY users (15%): {user_types['crazy']}")
        
        # Create markets
        self.stdout.write('\n[2.2] Creating synthetic markets...')
        synthetic_markets = self._create_synthetic_markets(category, synthetic_users)
        self.stdout.write(f"✓ Created {len(synthetic_markets)} synthetic markets")
        
        # Create trades
        self.stdout.write('\n[2.3] Creating synthetic trades...')
        all_trades = self._create_synthetic_trades(synthetic_users, synthetic_markets, user_types)
        self.stdout.write(f"✓ Created {len(all_trades)} synthetic trades")
        
        # Create outcome tokens
        self.stdout.write('\n[2.4] Creating synthetic outcome tokens...')
        outcome_tokens_count = self._create_synthetic_outcome_tokens(synthetic_markets, all_trades)
        self.stdout.write(f"✓ Created {outcome_tokens_count} outcome tokens")
        
        # Create positions
        self.stdout.write('\n[2.5] Creating synthetic positions...')
        positions_count = self._create_synthetic_positions(all_trades)
        self.stdout.write(f"✓ Created {positions_count} positions")
        
        # Create liquidity events
        self.stdout.write('\n[2.6] Creating synthetic liquidity events...')
        liquidity_events_count = self._create_synthetic_liquidity_events(synthetic_markets, synthetic_users)
        self.stdout.write(f"✓ Created {liquidity_events_count} liquidity events")
        
        # Create resolutions and disputes
        self.stdout.write('\n[2.7] Creating synthetic resolutions and disputes...')
        resolutions_count, disputes_count = self._create_synthetic_resolutions_and_disputes(
            synthetic_markets, synthetic_users
        )
        self.stdout.write(f"✓ Created {resolutions_count} resolutions")
        self.stdout.write(f"✓ Created {disputes_count} disputes")
        
        # Create price history
        self.stdout.write('\n[2.8] Creating synthetic price history...')
        price_history_count = self._create_synthetic_price_history(synthetic_markets)
        self.stdout.write(f"✓ Created {price_history_count} price history entries")
        
        # Create onchain data
        self.stdout.write('\n[2.9] Creating synthetic onchain data...')
        onchain_tx_count, onchain_event_count = self._create_synthetic_onchain_data(
            synthetic_markets, synthetic_users, all_trades
        )
        if onchain_tx_count > 0:
            self.stdout.write(f"✓ Created {onchain_tx_count} onchain transactions")
            self.stdout.write(f"✓ Created {onchain_event_count} onchain event logs")
        else:
            self.stdout.write("  → Onchain models not available, skipped")
        
        # Summary
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('FULL SYNTHETIC DATA RESET AND SEEDING COMPLETED!'))
        self.stdout.write('=' * 70)
        self.stdout.write(f"  Synthetic Users: {len(synthetic_users)}")
        self.stdout.write(f"  Synthetic Markets: {len(synthetic_markets)}")
        self.stdout.write(f"  Synthetic Trades: {len(all_trades)}")
        self.stdout.write(f"  Outcome Tokens: {outcome_tokens_count}")
        self.stdout.write(f"  Positions: {positions_count}")
        self.stdout.write(f"  Liquidity Events: {liquidity_events_count}")
        self.stdout.write(f"  Resolutions: {resolutions_count}")
        self.stdout.write(f"  Disputes: {disputes_count}")
        self.stdout.write(f"  Price History Entries: {price_history_count}")
        self.stdout.write(f"  Onchain Transactions: {onchain_tx_count}")
        self.stdout.write(f"  Onchain Event Logs: {onchain_event_count}")
        self.stdout.write('\n✓ Data is ready for ML experiments:')
        self.stdout.write('  - Suspicious Trade Detection (IsolationForest)')
        self.stdout.write('  - Volatility / market behaviour analysis')
        self.stdout.write('  - User segmentation / behaviour analysis')

    def _cleanup_synthetic_data(self):
        """Safely delete all synthetic data in the correct order"""
        deleted_counts = {
            'disputes': 0,
            'resolutions': 0,
            'liquidity_events': 0,
            'price_history': 0,
            'outcome_tokens': 0,
            'trades': 0,
            'positions': 0,
            'onchain_event_logs': 0,
            'onchain_transactions': 0,
            'markets': 0,
            'users': 0,
        }
        
        # Get synthetic users and markets
        synthetic_users = User.objects.filter(email__startswith='synthetic_user')
        synthetic_markets = Market.objects.filter(title__startswith='Synthetic Market')
        
        # 1. Delete Disputes
        disputes_to_delete = Dispute.objects.filter(
            user__in=synthetic_users
        ) | Dispute.objects.filter(
            market__in=synthetic_markets
        )
        deleted_counts['disputes'] = disputes_to_delete.count()
        disputes_to_delete.delete()
        if deleted_counts['disputes'] > 0:
            self.stdout.write(f"  ✓ Deleted {deleted_counts['disputes']} synthetic disputes")
        
        # 2. Delete Resolutions
        resolutions_to_delete = Resolution.objects.filter(market__in=synthetic_markets)
        deleted_counts['resolutions'] = resolutions_to_delete.count()
        resolutions_to_delete.delete()
        if deleted_counts['resolutions'] > 0:
            self.stdout.write(f"  ✓ Deleted {deleted_counts['resolutions']} synthetic resolutions")
        
        # 3. Delete LiquidityEvents
        liquidity_events_to_delete = LiquidityEvent.objects.filter(
            user__in=synthetic_users
        ) | LiquidityEvent.objects.filter(
            market__in=synthetic_markets
        )
        deleted_counts['liquidity_events'] = liquidity_events_to_delete.count()
        liquidity_events_to_delete.delete()
        if deleted_counts['liquidity_events'] > 0:
            self.stdout.write(f"  ✓ Deleted {deleted_counts['liquidity_events']} synthetic liquidity events")
        
        # 4. Delete PriceHistory
        price_history_to_delete = PriceHistory.objects.filter(market__in=synthetic_markets)
        deleted_counts['price_history'] = price_history_to_delete.count()
        price_history_to_delete.delete()
        if deleted_counts['price_history'] > 0:
            self.stdout.write(f"  ✓ Deleted {deleted_counts['price_history']} price history entries")
        
        # 5. Delete OutcomeTokens
        outcome_tokens_to_delete = OutcomeToken.objects.filter(market__in=synthetic_markets)
        deleted_counts['outcome_tokens'] = outcome_tokens_to_delete.count()
        outcome_tokens_to_delete.delete()
        if deleted_counts['outcome_tokens'] > 0:
            self.stdout.write(f"  ✓ Deleted {deleted_counts['outcome_tokens']} outcome tokens")
        
        # 6. Delete Trades
        trades_to_delete = Trade.objects.filter(
            user__in=synthetic_users
        ) | Trade.objects.filter(
            market__in=synthetic_markets
        )
        deleted_counts['trades'] = trades_to_delete.count()
        trades_to_delete.delete()
        if deleted_counts['trades'] > 0:
            self.stdout.write(f"  ✓ Deleted {deleted_counts['trades']} synthetic trades")
        
        # 7. Delete Positions
        positions_to_delete = Position.objects.filter(
            user__in=synthetic_users
        ) | Position.objects.filter(
            market__in=synthetic_markets
        )
        deleted_counts['positions'] = positions_to_delete.count()
        positions_to_delete.delete()
        if deleted_counts['positions'] > 0:
            self.stdout.write(f"  ✓ Deleted {deleted_counts['positions']} synthetic positions")
        
        # 8. Delete OnchainEventLogs (if model exists)
        if HAS_ONCHAIN_MODELS:
            onchain_event_logs_to_delete = OnchainEventLog.objects.filter(
                market__in=synthetic_markets
            )
            deleted_counts['onchain_event_logs'] = onchain_event_logs_to_delete.count()
            onchain_event_logs_to_delete.delete()
            if deleted_counts['onchain_event_logs'] > 0:
                self.stdout.write(f"  ✓ Deleted {deleted_counts['onchain_event_logs']} onchain event logs")
            
            # 9. Delete OnchainTransactions (only those linked to synthetic data)
            # Get tx hashes from deleted event logs or synthetic trades
            synthetic_tx_hashes = set()
            synthetic_tx_hashes.update(
                Trade.objects.filter(user__in=synthetic_users).values_list('onchain_tx_hash', flat=True)
            )
            synthetic_tx_hashes.update(
                Market.objects.filter(title__startswith='Synthetic Market').values_list('onchain_tx_hash', flat=True)
            )
            synthetic_tx_hashes = {h for h in synthetic_tx_hashes if h}
            
            if synthetic_tx_hashes:
                onchain_tx_to_delete = OnchainTransaction.objects.filter(tx_hash__in=synthetic_tx_hashes)
                deleted_counts['onchain_transactions'] = onchain_tx_to_delete.count()
                onchain_tx_to_delete.delete()
                if deleted_counts['onchain_transactions'] > 0:
                    self.stdout.write(f"  ✓ Deleted {deleted_counts['onchain_transactions']} onchain transactions")
        
        # 10. Delete Markets
        deleted_counts['markets'] = synthetic_markets.count()
        synthetic_markets.delete()
        if deleted_counts['markets'] > 0:
            self.stdout.write(f"  ✓ Deleted {deleted_counts['markets']} synthetic markets")
        
        # 11. Delete Users
        deleted_counts['users'] = synthetic_users.count()
        synthetic_users.delete()
        if deleted_counts['users'] > 0:
            self.stdout.write(f"  ✓ Deleted {deleted_counts['users']} synthetic users")
        
        if sum(deleted_counts.values()) == 0:
            self.stdout.write("  → No existing synthetic data found")

    def _create_synthetic_users(self):
        """Create 500 synthetic users with different behavior types"""
        users = []
        total_users = 500
        
        # Calculate user type distribution
        num_passive = int(total_users * 0.15)  # 15% = 75 users
        num_normal = int(total_users * 0.70)  # 70% = 350 users
        num_crazy = total_users - num_passive - num_normal  # 15% = 75 users
        
        # Assign user types
        passive_indices = set(random.sample(range(total_users), num_passive))
        remaining = [i for i in range(total_users) if i not in passive_indices]
        normal_indices = set(random.sample(remaining, num_normal))
        crazy_indices = set(range(total_users)) - passive_indices - normal_indices
        
        for i in range(total_users):
            username = f'synthetic_user_{i}'
            email = f'synthetic_user_{i}@example.com'
            
            # Determine user type
            if i in crazy_indices:
                user_type = 'crazy'
            elif i in normal_indices:
                user_type = 'normal'
            else:
                user_type = 'passive'
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password='test1234',
            )
            
            # Set additional fields if they exist
            if hasattr(user, 'role'):
                user.role = 'user'
            if hasattr(user, 'total_points'):
                user.total_points = Decimal('0.0')
            if hasattr(user, 'win_rate'):
                user.win_rate = Decimal('0.0')
            if hasattr(user, 'streak'):
                user.streak = 0
            
            user.save()
            users.append((user, user_type))
            
            if (i + 1) % 100 == 0:
                self.stdout.write(f"  → Created {i + 1}/{total_users} users...")
        
        user_type_counts = {
            'passive': num_passive,
            'normal': num_normal,
            'crazy': num_crazy,
        }
        
        return users, user_type_counts

    def _create_synthetic_markets(self, category, users):
        """Create 30 synthetic markets"""
        markets = []
        creator = users[0][0] if users else None  # Use first synthetic user as creator
        
        for i in range(30):
            title = f'Synthetic Market {i}'
            description = 'Synthetic market for ML testing'
            
            # Random end date between now and 30 days
            days_ahead = random.randint(1, 30)
            ends_at = timezone.now() + timedelta(days=days_ahead)
            
            # Random liquidity pool
            liquidity_pool = Decimal(str(random.uniform(1000, 10000))).quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP,
            )
            
            market_data = {
                'title': title,
                'description': description,
                'status': 'active',
                'ends_at': ends_at,
                'liquidity_pool': liquidity_pool,
                'fee_percentage': Decimal('0.02'),
                'onchain_market_id': None,
                'onchain_tx_hash': f'synthetic_market_{i}',
            }
            
            # Add category if it exists
            if category:
                market_data['category'] = category
            
            # Add creator if field exists
            if creator and hasattr(Market, 'created_by'):
                market_data['created_by'] = creator
            
            try:
                market = Market.objects.create(**market_data)
            except Exception as e:
                # If category is required but missing, try without it
                if 'category' in str(e):
                    market_data.pop('category', None)
                    market = Market.objects.create(**market_data)
                else:
                    raise
            
            markets.append(market)
        
        return markets

    def _create_synthetic_trades(self, users, markets, user_types):
        """Create 20-25 trades per active user with realistic timestamps"""
        all_trades = []
        
        for user, user_type in users:
            # Skip passive users
            if user_type == 'passive':
                continue
            
            # Determine trade parameters based on user type
            if user_type == 'crazy':
                amount_min, amount_max = 80, 500
                time_gap_min, time_gap_max = 1, 120  # 1-120 seconds
                num_trades = random.randint(20, 25)
            else:  # normal
                amount_min, amount_max = 1, 50
                time_gap_min, time_gap_max = 10, 3600  # 10-3600 seconds
                num_trades = random.randint(20, 25)
            
            # Start timestamp: random time in the past 7 days
            base_time = timezone.now() - timedelta(days=random.randint(0, 7))
            current_time = base_time
            
            # Create trades for this user
            for trade_num in range(num_trades):
                # Random market
                market = random.choice(markets)
                
                # Random outcome and trade type
                outcome_type = random.choice(['YES', 'NO'])
                trade_type = random.choice(['buy', 'sell'])
                
                # Amount staked based on user type
                amount_staked = Decimal(str(random.uniform(amount_min, amount_max))).quantize(
                    Decimal('0.01'),
                    rounding=ROUND_HALF_UP,
                )
                
                # Price varies between 0.3 and 0.7 for realism
                price_at_execution = Decimal(str(random.uniform(0.3, 0.7))).quantize(
                    Decimal('0.000001'),
                    rounding=ROUND_HALF_UP,
                )
                
                # Tokens amount = amount_staked / price
                tokens_amount = (amount_staked / price_at_execution).quantize(
                    Decimal('0.01'),
                    rounding=ROUND_HALF_UP,
                )
                
                # Generate fake onchain data
                fake_tx_hash = f'0x{random.randint(100000, 999999):06x}{random.randint(100000, 999999):06x}'
                fake_trade_id = random.randint(1000, 999999)
                
                # Create trade
                trade = Trade.objects.create(
                    user=user,
                    market=market,
                    outcome_type=outcome_type,
                    trade_type=trade_type,
                    amount_staked=amount_staked,
                    tokens_amount=tokens_amount,
                    price_at_execution=price_at_execution,
                    onchain_tx_hash=fake_tx_hash,
                    onchain_trade_id=fake_trade_id,
                )
                
                # Override created_at to use our custom timestamp
                trade.created_at = current_time
                trade.save(update_fields=['created_at'])
                
                all_trades.append(trade)
                
                # Increment time for next trade
                time_gap = random.randint(time_gap_min, time_gap_max)
                current_time = current_time + timedelta(seconds=time_gap)
            
            if len(all_trades) % 500 == 0:
                self.stdout.write(f"  → Created {len(all_trades)} trades...")
        
        return all_trades

    def _create_synthetic_outcome_tokens(self, markets, trades):
        """Create outcome tokens for each market based on trades"""
        total_created = 0
        
        for market in markets:
            # Get trades for this market
            market_trades = [t for t in trades if t.market_id == market.id]
            
            # Calculate supply from trades
            yes_supply = Decimal('0')
            no_supply = Decimal('0')
            yes_prices = []
            no_prices = []
            
            for trade in market_trades:
                if trade.outcome_type == 'YES' and trade.trade_type == 'buy':
                    yes_supply += trade.tokens_amount
                    yes_prices.append(trade.price_at_execution)
                elif trade.outcome_type == 'NO' and trade.trade_type == 'buy':
                    no_supply += trade.tokens_amount
                    no_prices.append(trade.price_at_execution)
                elif trade.outcome_type == 'YES' and trade.trade_type == 'sell':
                    yes_supply = max(Decimal('0'), yes_supply - trade.tokens_amount)
                elif trade.outcome_type == 'NO' and trade.trade_type == 'sell':
                    no_supply = max(Decimal('0'), no_supply - trade.tokens_amount)
            
            # Fallback if no trades
            if yes_supply == 0 and no_supply == 0:
                yes_supply = Decimal(str(random.uniform(100, 10000))).quantize(
                    Decimal('0.01'),
                    rounding=ROUND_HALF_UP,
                )
                no_supply = Decimal(str(random.uniform(100, 10000))).quantize(
                    Decimal('0.01'),
                    rounding=ROUND_HALF_UP,
                )
            
            # Calculate average prices or use defaults
            yes_price = Decimal(str(sum(yes_prices) / len(yes_prices))).quantize(
                Decimal('0.000001'),
                rounding=ROUND_HALF_UP,
            ) if yes_prices else Decimal('0.5')
            
            no_price = Decimal(str(sum(no_prices) / len(no_prices))).quantize(
                Decimal('0.000001'),
                rounding=ROUND_HALF_UP,
            ) if no_prices else Decimal('0.5')
            
            # Ensure prices are reasonable
            yes_price = max(Decimal('0.2'), min(Decimal('0.8'), yes_price))
            no_price = Decimal('1.0') - yes_price
            
            # Create outcome tokens
            now = timezone.now()
            
            yes_token, _ = OutcomeToken.objects.get_or_create(
                market=market,
                outcome_type='YES',
                defaults={
                    'price': yes_price,
                    'supply': yes_supply,
                    'created_at': now,
                    'updated_at': now,
                }
            )
            total_created += 1
            
            no_token, _ = OutcomeToken.objects.get_or_create(
                market=market,
                outcome_type='NO',
                defaults={
                    'price': no_price,
                    'supply': no_supply,
                    'created_at': now,
                    'updated_at': now,
                }
            )
            total_created += 1
        
        return total_created

    def _create_synthetic_positions(self, trades):
        """Create positions aggregated from trades"""
        positions_created = 0
        
        # Group trades by (user, market)
        user_market_trades = defaultdict(list)
        
        for trade in trades:
            key = (trade.user_id, trade.market_id)
            user_market_trades[key].append(trade)
        
        # Create position for each (user, market) pair
        for (user_id, market_id), trade_list in user_market_trades.items():
            # Sort trades by created_at
            trade_list.sort(key=lambda t: t.created_at)
            
            # Aggregate position
            yes_tokens = Decimal('0')
            no_tokens = Decimal('0')
            total_staked = Decimal('0')
            
            for trade in trade_list:
                total_staked += trade.amount_staked
                
                if trade.outcome_type == 'YES':
                    if trade.trade_type == 'buy':
                        yes_tokens += trade.tokens_amount
                    else:  # sell
                        yes_tokens = max(Decimal('0'), yes_tokens - trade.tokens_amount)
                else:  # NO
                    if trade.trade_type == 'buy':
                        no_tokens += trade.tokens_amount
                    else:  # sell
                        no_tokens = max(Decimal('0'), no_tokens - trade.tokens_amount)
            
            # Create or update position
            position, created = Position.objects.get_or_create(
                user_id=user_id,
                market_id=market_id,
                defaults={
                    'yes_tokens': yes_tokens,
                    'no_tokens': no_tokens,
                    'total_staked': total_staked,
                    'created_at': trade_list[0].created_at,
                    'updated_at': trade_list[-1].created_at,
                }
            )
            
            if not created:
                # Update existing position
                position.yes_tokens = yes_tokens
                position.no_tokens = no_tokens
                position.total_staked = total_staked
                position.updated_at = trade_list[-1].created_at
                position.save()
            
            positions_created += 1
        
        return positions_created

    def _create_synthetic_liquidity_events(self, markets, users):
        """Create liquidity events for each market"""
        total_created = 0
        
        for market in markets:
            num_events = random.randint(10, 15)
            base_time = timezone.now() - timedelta(days=random.randint(0, 7))
            current_time = base_time
            
            for _ in range(num_events):
                user = random.choice([u[0] for u in users])
                event_type = random.choice(['add', 'remove'])
                amount = Decimal(str(random.uniform(50, 500))).quantize(
                    Decimal('0.01'),
                    rounding=ROUND_HALF_UP,
                )
                
                fake_tx_hash = f'0x{random.randint(100000, 999999):06x}{random.randint(100000, 999999):06x}'
                fake_liquidity_id = random.randint(1000, 999999)
                
                event = LiquidityEvent.objects.create(
                    market=market,
                    user=user,
                    event_type=event_type,
                    amount=amount,
                    onchain_tx_hash=fake_tx_hash,
                    onchain_liquidity_id=fake_liquidity_id,
                )
                
                # Override created_at
                event.created_at = current_time
                event.save(update_fields=['created_at'])
                
                total_created += 1
                
                # Move forward in time
                hours_gap = random.randint(1, 24)
                current_time = current_time + timedelta(hours=hours_gap)
        
        return total_created

    def _create_synthetic_resolutions_and_disputes(self, markets, users):
        """Create resolutions for half the markets, and disputes for some resolved markets"""
        resolutions_count = 0
        disputes_count = 0
        
        # Resolve half the markets
        markets_to_resolve = random.sample(markets, len(markets) // 2)
        resolver = users[0][0] if users else None
        
        for market in markets_to_resolve:
            # Determine resolved outcome (could align with majority trades, but for simplicity, random)
            resolved_outcome = random.choice(['YES', 'NO'])
            
            # Resolution created after market ends
            resolution_time = market.ends_at + timedelta(hours=random.randint(1, 24))
            dispute_window_seconds = 3600  # 1 hour
            
            fake_tx_hash = f'0x{random.randint(100000, 999999):06x}{random.randint(100000, 999999):06x}'
            
            resolution_data = {
                'market': market,
                'resolved_outcome': resolved_outcome,
                'dispute_window': resolution_time + timedelta(seconds=dispute_window_seconds),
                'bond_amount': Decimal(str(random.uniform(10, 100))).quantize(
                    Decimal('0.01'),
                    rounding=ROUND_HALF_UP,
                ),
                'onchain_tx_hash': fake_tx_hash,
            }
            
            if resolver and hasattr(Resolution, 'resolver'):
                resolution_data['resolver'] = resolver
            
            resolution = Resolution.objects.create(**resolution_data)
            
            # Override created_at
            resolution.created_at = resolution_time
            resolution.save(update_fields=['created_at'])
            
            resolutions_count += 1
            
            # Create disputes for some resolved markets
            if random.random() < 0.5:  # 50% chance
                num_disputes = random.randint(10, 100)
                dispute_users = random.sample([u[0] for u in users], min(num_disputes, len(users)))
                
                for dispute_user in dispute_users:
                    status = random.choice(['pending', 'accepted', 'rejected'])
                    bond_amount = Decimal(str(random.uniform(5, 50))).quantize(
                        Decimal('0.01'),
                        rounding=ROUND_HALF_UP,
                    )
                    
                    reasons = [
                        'Suspicious resolution',
                        'Price manipulation detected',
                        'Incorrect outcome',
                        'Market manipulation',
                        'Unfair resolution',
                    ]
                    reason = random.choice(reasons)
                    
                    dispute = Dispute.objects.create(
                        market=market,
                        user=dispute_user,
                        bond_amount=bond_amount,
                        status=status,
                        reason=reason,
                    )
                    
                    # Set timestamps
                    dispute.created_at = resolution_time + timedelta(
                        seconds=random.randint(0, dispute_window_seconds)
                    )
                    dispute.save(update_fields=['created_at'])
                    
                    # Set resolved_at if status is not pending
                    if status != 'pending':
                        dispute.resolved_at = dispute.created_at + timedelta(
                            hours=random.randint(1, 48)
                        )
                        dispute.save(update_fields=['resolved_at'])
                    
                    disputes_count += 1
        
        return resolutions_count, disputes_count

    def _create_synthetic_price_history(self, markets):
        """Create realistic price history for each market"""
        total_created = 0
        
        for market in markets:
            # Generate price history over the last 7 days
            base_time = timezone.now() - timedelta(days=7)
            current_time = base_time
            
            # Start with prices around 0.5
            yes_price = Decimal('0.5')
            no_price = Decimal('0.5')
            
            # Generate 10-30 price points per market
            num_points = random.randint(10, 30)
            
            for _ in range(num_points):
                # Price fluctuates but stays between 0.2 and 0.8
                price_change = Decimal(str(random.uniform(-0.05, 0.05)))
                yes_price = max(Decimal('0.2'), min(Decimal('0.8'), yes_price + price_change))
                no_price = Decimal('1.0') - yes_price
                
                price_history = PriceHistory.objects.create(
                    market=market,
                    yes_price=yes_price.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP),
                    no_price=no_price.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP),
                )
                
                # Override timestamp
                price_history.timestamp = current_time
                price_history.save(update_fields=['timestamp'])
                
                total_created += 1
                
                # Move forward in time
                hours_gap = random.randint(1, 12)
                current_time = current_time + timedelta(hours=hours_gap)
        
        return total_created

    def _create_synthetic_onchain_data(self, markets, users, trades):
        """Create onchain transactions and event logs"""
        if not HAS_ONCHAIN_MODELS:
            return 0, 0
        
        onchain_tx_count = 0
        onchain_event_count = 0
        
        # Collect unique tx hashes from trades and markets
        tx_hashes = set()
        for trade in trades[:100]:  # Limit to first 100 trades
            if trade.onchain_tx_hash:
                tx_hashes.add(trade.onchain_tx_hash)
        
        for market in markets:
            if market.onchain_tx_hash:
                tx_hashes.add(market.onchain_tx_hash)
        
        # Create additional synthetic transactions
        for _ in range(50):
            fake_tx_hash = f'0x{random.randint(100000, 999999):06x}{random.randint(100000, 999999):06x}'
            tx_hashes.add(fake_tx_hash)
        
        # Create OnchainTransaction records
        for tx_hash in tx_hashes:
            tx, created = OnchainTransaction.objects.get_or_create(
                tx_hash=tx_hash,
                defaults={
                    'network': 'testnet',
                    'block_number': random.randint(1000000, 9999999),
                    'status': 'SUCCESS',
                    'error_message': '',
                }
            )
            
            if created:
                onchain_tx_count += 1
                
                # Create 1-3 event logs per transaction
                num_events = random.randint(1, 3)
                event_names = ['TradeExecuted', 'LiquidityAdded', 'MarketResolved', 'LiquidityRemoved']
                
                for log_index in range(num_events):
                    event_name = random.choice(event_names)
                    market = random.choice(markets) if random.random() < 0.7 else None
                    user_address = f'0x{random.randint(100000, 999999):06x}'
                    
                    payload = {
                        'amount': float(random.uniform(1, 100)),
                        'outcome': random.choice(['YES', 'NO']) if event_name == 'TradeExecuted' else None,
                    }
                    
                    event_log = OnchainEventLog.objects.create(
                        onchain_tx=tx,
                        event_name=event_name,
                        tx_hash=tx_hash,
                        log_index=log_index,
                        market=market,
                        user_address=user_address,
                        payload_json=payload,
                        processed_at=timezone.now(),
                        duplicate=False,
                    )
                    
                    onchain_event_count += 1
        
        return onchain_tx_count, onchain_event_count

