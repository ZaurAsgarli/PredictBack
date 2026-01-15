"""
Management command to seed logs and events for Admin Dashboard testing.
"""
import random
import logging
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from faker import Faker

from backend_api.api.users.models import User
from backend_api.api.markets.models import Market
from backend_api.api.trades.models import Trade
from backend_api.api.liquidity.models import LiquidityEvent
from backend_api.api.indexer.models import OnchainTransaction, OnchainEventLog
from security_engine.models import SecurityLog, LoginAttempt
from ml_service.training.models import TradeRiskPrediction

fake = Faker()

transactions_logger = logging.getLogger('transactions')
security_logger = logging.getLogger('security')
ml_logger = logging.getLogger('ml_engine')


class Command(BaseCommand):
    help = 'Seed log/event tables with realistic synthetic data for Admin Dashboard'

    def add_arguments(self, parser):
        parser.add_argument('--security-count', type=int, default=250)
        parser.add_argument('--liquidity-percent', type=int, default=30)
        parser.add_argument('--high-risk-users', type=int, default=8)

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Starting Log Seeder...'))
        
        users = list(User.objects.all())
        markets = list(Market.objects.all())
        trades = list(Trade.objects.all())
        
        if not users:
            self.stdout.write(self.style.ERROR('No users found! Run seed_ultimate first.'))
            return
        
        if not markets:
            self.stdout.write(self.style.ERROR('No markets found! Run seed_ultimate first.'))
            return
        
        self.stdout.write(f'Found {len(users)} users, {len(markets)} markets, {len(trades)} trades')
        
        sorted_users = sorted(users, key=lambda u: u.total_points, reverse=True)
        whale_count = max(1, len(sorted_users) // 5)
        whale_users = sorted_users[:whale_count]
        
        self.stdout.write(f'Identified {len(whale_users)} whale users')
        
        with transaction.atomic():
            liquidity_count = self.seed_liquidity_events(markets, whale_users, options['liquidity_percent'])
            security_count = self.seed_security_logs(users, options['security_count'])
            ml_count = self.seed_ml_logs(users, trades, options['high_risk_users'])
            tx_count = self.seed_transaction_logs(trades, markets)
        
        self.stdout.write(self.style.SUCCESS(
            f'\nSeeding Complete!\n'
            f'   - LiquidityEvents: {liquidity_count}\n'
            f'   - SecurityLogs: {security_count}\n'
            f'   - TradeRiskPredictions: {ml_count}\n'
            f'   - OnchainTransactions: {tx_count}'
        ))

    def seed_liquidity_events(self, markets, whale_users, percent):
        self.stdout.write('Seeding LiquidityEvents...')
        
        target_markets = random.sample(markets, max(1, len(markets) * percent // 100))
        events = []
        now = timezone.now()
        
        for market in target_markets:
            event_count = random.randint(1, 5)
            for _ in range(event_count):
                user = random.choice(whale_users)
                event_type = random.choice(['add', 'add', 'add', 'remove'])
                amount = Decimal(str(random.uniform(500, 50000))).quantize(Decimal('0.01'))
                
                days_ago = random.randint(0, 30)
                hours_ago = random.randint(0, 23)
                created_at = now - timedelta(days=days_ago, hours=hours_ago)
                
                event = LiquidityEvent(
                    market=market,
                    user=user,
                    event_type=event_type,
                    amount=amount,
                    onchain_tx_hash=f'0x{fake.hexify(text="^" * 64)}',
                    created_at=created_at
                )
                events.append(event)
                
                transactions_logger.info(
                    f'[USER:{user.id}] LIQUIDITY_{event_type.upper()} '
                    f'amount={amount} market_id={market.id}'
                )
        
        LiquidityEvent.objects.bulk_create(events, ignore_conflicts=True)
        return len(events)

    def seed_security_logs(self, users, count):
        self.stdout.write('Seeding SecurityLogs...')
        
        severity_weights = ['LOW'] * 60 + ['MEDIUM'] * 25 + ['HIGH'] * 10 + ['CRITICAL'] * 5
        
        event_types = [
            ('RATE_LIMIT', 'Rate limit exceeded from IP'),
            ('FAILED_LOGIN', 'Failed login attempt for user'),
            ('UNAUTHORIZED_ACCESS', 'Unauthorized API access attempt'),
            ('SUSPICIOUS_ACTIVITY', 'Suspicious trading pattern detected'),
        ]
        
        critical_messages = [
            'DDoS attack pattern detected from IP range',
            'SQL injection attempt blocked',
            'Brute force attack in progress',
            'Credential stuffing attack detected',
            'API abuse: 1000+ requests in 60 seconds',
        ]
        
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
            'python-requests/2.28.1',
            'curl/7.79.1',
        ]
        
        logs = []
        now = timezone.now()
        
        for i in range(count):
            severity = random.choice(severity_weights)
            event_type, base_message = random.choice(event_types)
            
            if severity == 'CRITICAL':
                message = random.choice(critical_messages)
                event_type = 'SUSPICIOUS_ACTIVITY'
            else:
                user = random.choice(users) if users else None
                message = f'{base_message}: {user.email if user else "unknown"}'
            
            if severity in ['HIGH', 'CRITICAL']:
                ip = f'{random.choice([185, 45, 103, 194])}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}'
            else:
                ip = fake.ipv4()
            
            days_ago = random.randint(0, 14)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            timestamp = now - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
            
            log = SecurityLog(
                ip=ip,
                event_type=event_type,
                severity=severity,
                message=message,
                path=random.choice(['/api/users/login/', '/api/trades/', '/api/markets/', '/api/admin/']),
                user_agent=random.choice(user_agents),
                user=random.choice(users) if random.random() > 0.3 and users else None,
                metadata={'request_count': random.randint(1, 100), 'blocked': severity in ['HIGH', 'CRITICAL']}
            )
            logs.append(log)
            
            # Map severity to Python logging level
            severity_to_level = {
                'LOW': 'info',
                'MEDIUM': 'warning', 
                'HIGH': 'error',
                'CRITICAL': 'critical'
            }
            log_method = getattr(security_logger, severity_to_level.get(severity, 'info'))
            log_method(f'[IP:{ip}] {event_type}: {message}')
        
        SecurityLog.objects.bulk_create(logs, ignore_conflicts=True)
        return len(logs)

    def seed_ml_logs(self, users, trades, high_risk_count):
        self.stdout.write('Seeding ML Logs (TradeRiskPrediction)...')
        
        high_risk_users = random.sample(users, min(high_risk_count, len(users)))
        
        risk_reasons = [
            'High Velocity Trading: 50+ trades in 1 hour',
            'New Wallet Large Deposit: First deposit >$10,000',
            'Unusual Pattern: Trades only on one outcome',
            'Whale Activity: Single trade >20% of market liquidity',
            'Bot-like Behavior: Sub-second trade execution',
        ]
        
        predictions = []
        
        # High-risk users (anomaly detected)
        for user in high_risk_users:
            user_trades = [t for t in trades if t.user_id == user.id]
            trade = user_trades[0] if user_trades else None
            
            # score is FloatField in range -1 to 1 - higher negative = more anomalous
            score = random.uniform(-0.9, -0.5)  # High risk = negative score
            
            prediction = TradeRiskPrediction(
                user=user,
                trade=trade,
                market=trade.market if trade else None,
                score=score,
                label=-1,  # -1 = anomaly
                risk_level='CRITICAL' if score < -0.8 else 'HIGH',
                model_version='v2.1-suspicious-detector',
                amount_staked=trade.amount_staked if trade else None,
            )
            predictions.append(prediction)
            
            reason = random.choice(risk_reasons)
            ml_logger.warning(
                f'[USER:{user.id}] HIGH_RISK_DETECTED score={score:.3f} reason="{reason}"'
            )
        
        # Normal users
        normal_users = [u for u in users if u not in high_risk_users][:20]
        for user in normal_users:
            user_trades = [t for t in trades if t.user_id == user.id]
            trade = user_trades[0] if user_trades else None
            
            # Normal behavior = positive score
            score = random.uniform(0.1, 0.8)
            risk_level = 'LOW' if score > 0.5 else 'MEDIUM'
            
            prediction = TradeRiskPrediction(
                user=user,
                trade=trade,
                market=trade.market if trade else None,
                score=score,
                label=1,  # 1 = normal
                risk_level=risk_level,
                model_version='v2.1-suspicious-detector',
                amount_staked=trade.amount_staked if trade else None,
            )
            predictions.append(prediction)
            
            ml_logger.info(f'[USER:{user.id}] RISK_ASSESSED score={score:.3f} level={risk_level}')
        
        TradeRiskPrediction.objects.bulk_create(predictions, ignore_conflicts=True)
        return len(predictions)

    def seed_transaction_logs(self, trades, markets):
        self.stdout.write('Seeding Transaction Logs...')
        
        transactions = []
        events = []
        now = timezone.now()
        
        for trade in trades[:100]:
            if trade.onchain_tx_hash:
                continue
            
            tx_hash = f'0x{fake.hexify(text="^" * 64)}'
            block_number = random.randint(18000000, 19000000)
            
            tx = OnchainTransaction(
                tx_hash=tx_hash,
                network='sepolia',
                block_number=block_number,
                status='SUCCESS',
                created_at=trade.created_at,
            )
            transactions.append(tx)
            
            transactions_logger.info(
                f'[USER:{trade.user_id}] TRADE_{trade.trade_type.upper()} '
                f'market_id={trade.market_id} amount={trade.amount_staked}'
            )
        
        if transactions:
            OnchainTransaction.objects.bulk_create(transactions, ignore_conflicts=True)
        
        for market in markets[:30]:
            tx_hash = f'0x{fake.hexify(text="^" * 64)}'
            
            event = OnchainEventLog(
                event_name=random.choice(['MarketCreated', 'TradePlaced', 'LiquidityAdded']),
                tx_hash=tx_hash,
                log_index=random.randint(0, 10),
                market=market,
                payload_json={
                    'marketId': market.id,
                    'blockNumber': random.randint(18000000, 19000000),
                    'gasUsed': random.randint(50000, 200000),
                },
                processed_at=now,
            )
            events.append(event)
        
        if events:
            OnchainEventLog.objects.bulk_create(events, ignore_conflicts=True)
        
        return len(transactions) + len(events)
