"""
FINALIZE SYSTEM STATE
=====================
Post-simulation polish script that:
1. Creates Django Groups & Permissions
2. Maps Users to Groups based on Role
3. Creates Contract Event Logs from existing Trades/Disputes
4. Calculates User Positions (Portfolio) from trade history
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum
from django.utils import timezone
from backend_api.api.users.models import User
from backend_api.api.trades.models import Trade
from backend_api.api.markets.models import Market, OutcomeToken
from backend_api.api.positions.models import Position
from backend_api.api.liquidity.models import LiquidityEvent
from backend_api.api.disputes.models import Dispute
from backend_api.api.indexer.models import OnchainTransaction, OnchainEventLog
from decimal import Decimal
import json
import random


class Command(BaseCommand):
    help = 'Finalizes system state: Groups, Event Logs, Positions'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("=" * 70))
        self.stdout.write(self.style.WARNING("🔧 FINALIZING SYSTEM STATE"))
        self.stdout.write(self.style.WARNING("=" * 70))
        
        # ============================================================
        # STEP 1: PERMISSIONS & GROUPS
        # ============================================================
        self.stdout.write(self.style.SUCCESS("\n[STEP 1] Creating Groups & Permissions..."))
        
        # 1.1 Create Groups
        superadmins_group, _ = Group.objects.get_or_create(name='SuperAdmins')
        whales_group, _ = Group.objects.get_or_create(name='Whales')
        market_makers_group, _ = Group.objects.get_or_create(name='MarketMakers')
        
        self.stdout.write(f"  ✓ Created/Verified Groups: SuperAdmins, Whales, MarketMakers")
        
        # 1.2 Assign Permissions to SuperAdmins
        try:
            # Get content types for our models
            market_ct = ContentType.objects.get_for_model(Market)
            dispute_ct = ContentType.objects.get_for_model(Dispute)
            user_ct = ContentType.objects.get_for_model(User)
            
            # Get or create permissions
            admin_permissions = []
            
            # Market permissions
            for action in ['add', 'change', 'delete', 'view']:
                perm, _ = Permission.objects.get_or_create(
                    codename=f'{action}_market',
                    defaults={
                        'name': f'Can {action} market',
                        'content_type': market_ct
                    }
                )
                admin_permissions.append(perm)
            
            # Dispute permissions
            for action in ['add', 'change', 'delete', 'view']:
                perm, _ = Permission.objects.get_or_create(
                    codename=f'{action}_dispute',
                    defaults={
                        'name': f'Can {action} dispute',
                        'content_type': dispute_ct
                    }
                )
                admin_permissions.append(perm)
            
            # User ban permission
            ban_perm, _ = Permission.objects.get_or_create(
                codename='ban_user',
                defaults={
                    'name': 'Can ban user',
                    'content_type': user_ct
                }
            )
            admin_permissions.append(ban_perm)
            
            # Assign to SuperAdmins
            superadmins_group.permissions.add(*admin_permissions)
            self.stdout.write(f"  ✓ Assigned {len(admin_permissions)} permissions to SuperAdmins")
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  ⚠ Permission setup warning: {str(e)}"))
        
        # 1.3 Assign Custom Permissions to Whales
        try:
            whale_perms = []
            
            # Custom whale permissions
            view_analytics_perm, _ = Permission.objects.get_or_create(
                codename='view_advanced_analytics',
                defaults={
                    'name': 'Can view advanced analytics',
                    'content_type': user_ct
                }
            )
            whale_perms.append(view_analytics_perm)
            
            view_whale_chat_perm, _ = Permission.objects.get_or_create(
                codename='view_whale_chat',
                defaults={
                    'name': 'Can view whale chat',
                    'content_type': user_ct
                }
            )
            whale_perms.append(view_whale_chat_perm)
            
            whales_group.permissions.add(*whale_perms)
            self.stdout.write(f"  ✓ Assigned {len(whale_perms)} permissions to Whales")
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  ⚠ Whale permission warning: {str(e)}"))
        
        # 1.4 Map Users to Groups
        admin_count = 0
        whale_count = 0
        mm_count = 0
        
        for user in User.objects.all():
            if user.role == User.Role.ADMIN:
                superadmins_group.user_set.add(user)
                admin_count += 1
            elif user.role == User.Role.WHALE:
                whales_group.user_set.add(user)
                whale_count += 1
            elif 'MM_' in user.username or 'Provider' in user.username:
                market_makers_group.user_set.add(user)
                mm_count += 1
        
        self.stdout.write(f"  ✓ Mapped {admin_count} Admins to SuperAdmins group")
        self.stdout.write(f"  ✓ Mapped {whale_count} Whales to Whales group")
        self.stdout.write(f"  ✓ Mapped {mm_count} Market Makers to MarketMakers group")
        
        # ============================================================
        # STEP 2: CONTRACT EVENT LOGS
        # ============================================================
        self.stdout.write(self.style.SUCCESS("\n[STEP 2] Creating Contract Event Logs..."))
        
        event_count = 0
        
        # 2.1 Market Creation Events
        for market in Market.objects.all():
            if market.onchain_tx_hash:
                # Find or create the transaction
                tx, _ = OnchainTransaction.objects.get_or_create(
                    tx_hash=market.onchain_tx_hash,
                    defaults={
                        'network': 'sepolia',
                        'block_number': random.randint(15000000, 15100000),
                        'status': 'SUCCESS'
                    }
                )
                
                # Create event log
                OnchainEventLog.objects.get_or_create(
                    tx_hash=market.onchain_tx_hash,
                    log_index=0,
                    defaults={
                        'onchain_tx': tx,
                        'event_name': 'MarketCreated',
                        'market': market,
                        'user_address': market.created_by.wallet_address if market.created_by else '',
                        'payload_json': {
                            'marketId': market.onchain_market_id,
                            'title': market.title[:50],
                            'liquidity': str(market.liquidity_pool),
                            'creator': market.created_by.wallet_address if market.created_by else 'unknown'
                        }
                    }
                )
                event_count += 1
        
        self.stdout.write(f"  ✓ Created {event_count} MarketCreated events")
        
        # 2.2 Trade Execution Events
        trade_event_count = 0
        trades = Trade.objects.filter(onchain_tx_hash__isnull=False).select_related('user', 'market')[:500]  # Limit for performance
        
        for trade in trades:
            tx, _ = OnchainTransaction.objects.get_or_create(
                tx_hash=trade.onchain_tx_hash,
                defaults={
                    'network': 'sepolia',
                    'block_number': random.randint(15000000, 15200000),
                    'status': 'SUCCESS'
                }
            )
            
            OnchainEventLog.objects.get_or_create(
                tx_hash=trade.onchain_tx_hash,
                log_index=1,
                defaults={
                    'onchain_tx': tx,
                    'event_name': 'TradeExecuted',
                    'market': trade.market,
                    'user_address': trade.user.wallet_address if trade.user.wallet_address else '',
                    'payload_json': {
                        'trader': trade.user.wallet_address if trade.user.wallet_address else 'unknown',
                        'amount': str(trade.amount_staked),
                        'outcome': trade.outcome_type,
                        'tradeType': trade.trade_type,
                        'price': str(trade.price_at_execution),
                        'tokens': str(trade.tokens_amount)
                    }
                }
            )
            trade_event_count += 1
        
        self.stdout.write(f"  ✓ Created {trade_event_count} TradeExecuted events")
        
        # 2.3 Liquidity Events
        liq_event_count = 0
        for le in LiquidityEvent.objects.filter(onchain_tx_hash__isnull=False).select_related('user', 'market')[:100]:
            tx, _ = OnchainTransaction.objects.get_or_create(
                tx_hash=le.onchain_tx_hash,
                defaults={
                    'network': 'sepolia',
                    'block_number': random.randint(15000000, 15200000),
                    'status': 'SUCCESS'
                }
            )
            
            event_name = 'LiquidityAdded' if le.event_type == 'add' else 'LiquidityRemoved'
            
            OnchainEventLog.objects.get_or_create(
                tx_hash=le.onchain_tx_hash,
                log_index=0,
                defaults={
                    'onchain_tx': tx,
                    'event_name': event_name,
                    'market': le.market,
                    'user_address': le.user.wallet_address if le.user.wallet_address else '',
                    'payload_json': {
                        'provider': le.user.wallet_address if le.user.wallet_address else 'unknown',
                        'amount': str(le.amount),
                        'market': le.market.title[:30]
                    }
                }
            )
            liq_event_count += 1
        
        self.stdout.write(f"  ✓ Created {liq_event_count} Liquidity events")
        
        # 2.4 Dispute Events
        dispute_event_count = 0
        for dispute in Dispute.objects.select_related('user', 'market'):
            tx_hash = f'0x{hash(str(dispute.id)):064x}'[-66:]  # Generate deterministic hash
            
            tx, _ = OnchainTransaction.objects.get_or_create(
                tx_hash=tx_hash,
                defaults={
                    'network': 'sepolia',
                    'block_number': random.randint(15100000, 15200000),
                    'status': 'SUCCESS'
                }
            )
            
            OnchainEventLog.objects.get_or_create(
                tx_hash=tx_hash,
                log_index=0,
                defaults={
                    'onchain_tx': tx,
                    'event_name': 'DisputeRaised',
                    'market': dispute.market,
                    'user_address': dispute.user.wallet_address if dispute.user.wallet_address else '',
                    'payload_json': {
                        'disputant': dispute.user.wallet_address if dispute.user.wallet_address else 'unknown',
                        'bondAmount': str(dispute.bond_amount),
                        'reason': dispute.reason[:100],
                        'status': dispute.status
                    }
                }
            )
            dispute_event_count += 1
        
        self.stdout.write(f"  ✓ Created {dispute_event_count} DisputeRaised events")
        
        # ============================================================
        # STEP 3: POSITIONS CALCULATOR
        # ============================================================
        self.stdout.write(self.style.SUCCESS("\n[STEP 3] Calculating User Positions..."))
        
        position_count = 0
        
        # Get all users who have trades
        users_with_trades = User.objects.filter(trades__isnull=False).distinct()
        
        for user in users_with_trades:
            # Get all trades grouped by market
            user_trades = Trade.objects.filter(user=user).select_related('market')
            
            # Group trades by market
            market_trades = {}
            for trade in user_trades:
                if trade.market_id not in market_trades:
                    market_trades[trade.market_id] = {'YES': Decimal('0'), 'NO': Decimal('0'), 'staked': Decimal('0')}
                
                tokens = trade.tokens_amount if trade.tokens_amount else Decimal('0')
                
                if trade.trade_type == 'buy':
                    market_trades[trade.market_id][trade.outcome_type] += tokens
                else:  # sell
                    market_trades[trade.market_id][trade.outcome_type] -= tokens
                
                market_trades[trade.market_id]['staked'] += trade.amount_staked
            
            # Create positions
            for market_id, holdings in market_trades.items():
                yes_tokens = max(Decimal('0'), holdings['YES'])
                no_tokens = max(Decimal('0'), holdings['NO'])
                
                if yes_tokens > 0 or no_tokens > 0:
                    Position.objects.update_or_create(
                        user=user,
                        market_id=market_id,
                        defaults={
                            'yes_tokens': yes_tokens,
                            'no_tokens': no_tokens,
                            'total_staked': holdings['staked']
                        }
                    )
                    position_count += 1
        
        self.stdout.write(f"  ✓ Created/Updated {position_count} User Positions")
        
        # ============================================================
        # FINAL SUMMARY
        # ============================================================
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 70))
        self.stdout.write(self.style.SUCCESS("✅ SYSTEM STATE FINALIZED"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(f"  👥 Groups: {Group.objects.count()}")
        self.stdout.write(f"  🔐 Permissions: {Permission.objects.count()}")
        self.stdout.write(f"  📜 Contract Events: {OnchainEventLog.objects.count()}")
        self.stdout.write(f"  💼 User Positions: {Position.objects.count()}")
        self.stdout.write(self.style.SUCCESS("=" * 70))
