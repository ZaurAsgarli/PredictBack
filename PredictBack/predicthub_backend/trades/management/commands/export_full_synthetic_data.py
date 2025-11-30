"""
Django management command to export all synthetic data to CSV files for ML notebooks.
Exports: Users, Markets, Trades, Positions, OutcomeTokens, PriceHistory,
LiquidityEvents, Resolutions, Disputes, OnchainTransactions, OnchainEventLogs

Run with: python manage.py export_full_synthetic_data
"""
import os
import csv
import json
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.models import Q

from trades.models import Trade
from markets.models import Market, MarketCategory, OutcomeToken, PriceHistory, Resolution
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
    help = 'Exports all synthetic data to CSV files in ml/data/synthetic/'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('EXPORTING FULL SYNTHETIC DATA TO CSV'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        # Get output directory
        output_dir = self._get_output_dir()
        self.stdout.write(f'\nOutput directory: {output_dir}')
        
        # Get synthetic users and markets
        self.stdout.write('\n[FILTERING] Identifying synthetic data...')
        synthetic_users = User.objects.filter(email__startswith='synthetic_user_')
        synthetic_markets = Market.objects.filter(title__startswith='Synthetic Market')
        
        self.stdout.write(f"  ✓ Found {synthetic_users.count()} synthetic users")
        self.stdout.write(f"  ✓ Found {synthetic_markets.count()} synthetic markets")
        
        # Export each entity
        self.stdout.write('\n[EXPORTING] Exporting to CSV files...')
        
        self._export_users(synthetic_users, output_dir)
        self._export_markets(synthetic_markets, output_dir)
        self._export_trades(synthetic_users, synthetic_markets, output_dir)
        self._export_positions(synthetic_users, synthetic_markets, output_dir)
        self._export_outcome_tokens(synthetic_markets, output_dir)
        self._export_price_history(synthetic_markets, output_dir)
        self._export_liquidity_events(synthetic_users, synthetic_markets, output_dir)
        self._export_resolutions(synthetic_markets, output_dir)
        self._export_disputes(synthetic_users, synthetic_markets, output_dir)
        
        if HAS_ONCHAIN_MODELS:
            self._export_onchain_transactions(synthetic_users, synthetic_markets, output_dir)
            self._export_onchain_event_logs(synthetic_markets, output_dir)
        else:
            self.stdout.write(self.style.WARNING('  ⚠ Onchain models not available, skipping onchain exports'))
        
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('EXPORT COMPLETE!'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'\nAll CSV files saved to: {output_dir}')

    def _get_output_dir(self):
        """Get or create the output directory"""
        output_dir = os.path.join('ml', 'data', 'synthetic')
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    def _export_users(self, users_qs, output_dir):
        """Export synthetic users to CSV"""
        filepath = os.path.join(output_dir, 'users.csv')
        users = users_qs.values(
            'id', 'username', 'email', 'total_points', 'win_rate', 'streak', 'created_at'
        )
        
        if not users.exists():
            self.stdout.write(self.style.WARNING(f'  ⚠ No synthetic users found, skipping {filepath}'))
            return
        
        fieldnames = ['id', 'username', 'email', 'total_points', 'win_rate', 'streak', 'created_at']
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for user in users:
                row = {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'total_points': float(user['total_points']) if user['total_points'] else 0.0,
                    'win_rate': float(user['win_rate']) if user['win_rate'] else 0.0,
                    'streak': user['streak'] or 0,
                    'created_at': user['created_at'].isoformat() if user['created_at'] else '',
                }
                writer.writerow(row)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Exported {users.count()} synthetic users to {filepath}'))

    def _export_markets(self, markets_qs, output_dir):
        """Export synthetic markets to CSV"""
        filepath = os.path.join(output_dir, 'markets.csv')
        markets = markets_qs.values(
            'id', 'title', 'description', 'category_id', 'status', 'resolution_outcome',
            'liquidity_pool', 'fee_percentage', 'onchain_market_id', 'onchain_tx_hash',
            'created_by_id', 'created_at', 'ends_at'
        )
        
        if not markets.exists():
            self.stdout.write(self.style.WARNING(f'  ⚠ No synthetic markets found, skipping {filepath}'))
            return
        
        fieldnames = [
            'id', 'title', 'description', 'category_id', 'status', 'resolution_outcome',
            'liquidity_pool', 'fee_percentage', 'onchain_market_id', 'onchain_tx_hash',
            'created_by', 'created_at', 'ends_at'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for market in markets:
                row = {
                    'id': market['id'],
                    'title': market['title'],
                    'description': market['description'],
                    'category_id': market['category_id'],
                    'status': market['status'],
                    'resolution_outcome': market['resolution_outcome'] or '',
                    'liquidity_pool': float(market['liquidity_pool']) if market['liquidity_pool'] else 0.0,
                    'fee_percentage': float(market['fee_percentage']) if market['fee_percentage'] else 0.0,
                    'onchain_market_id': market['onchain_market_id'] or '',
                    'onchain_tx_hash': market['onchain_tx_hash'] or '',
                    'created_by': market['created_by_id'] or '',
                    'created_at': market['created_at'].isoformat() if market['created_at'] else '',
                    'ends_at': market['ends_at'].isoformat() if market['ends_at'] else '',
                }
                writer.writerow(row)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Exported {markets.count()} synthetic markets to {filepath}'))

    def _export_trades(self, synthetic_users, synthetic_markets, output_dir):
        """Export synthetic trades to CSV"""
        filepath = os.path.join(output_dir, 'trades.csv')
        trades = Trade.objects.filter(
            Q(user__in=synthetic_users) | Q(market__in=synthetic_markets)
        ).values(
            'id', 'user_id', 'market_id', 'outcome_type', 'trade_type',
            'amount_staked', 'tokens_amount', 'price_at_execution',
            'onchain_trade_id', 'onchain_tx_hash', 'created_at'
        )
        
        if not trades.exists():
            self.stdout.write(self.style.WARNING(f'  ⚠ No synthetic trades found, skipping {filepath}'))
            return
        
        fieldnames = [
            'id', 'user_id', 'market_id', 'outcome_type', 'trade_type',
            'amount_staked', 'tokens_amount', 'price_at_execution',
            'onchain_trade_id', 'onchain_tx_hash', 'created_at'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for trade in trades:
                row = {
                    'id': trade['id'],
                    'user_id': trade['user_id'],
                    'market_id': trade['market_id'],
                    'outcome_type': trade['outcome_type'],
                    'trade_type': trade['trade_type'],
                    'amount_staked': float(trade['amount_staked']) if trade['amount_staked'] else 0.0,
                    'tokens_amount': float(trade['tokens_amount']) if trade['tokens_amount'] else 0.0,
                    'price_at_execution': float(trade['price_at_execution']) if trade['price_at_execution'] else 0.0,
                    'onchain_trade_id': trade['onchain_trade_id'] or '',
                    'onchain_tx_hash': trade['onchain_tx_hash'] or '',
                    'created_at': trade['created_at'].isoformat() if trade['created_at'] else '',
                }
                writer.writerow(row)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Exported {trades.count()} synthetic trades to {filepath}'))

    def _export_positions(self, synthetic_users, synthetic_markets, output_dir):
        """Export synthetic positions to CSV"""
        filepath = os.path.join(output_dir, 'positions.csv')
        positions = Position.objects.filter(
            Q(user__in=synthetic_users) | Q(market__in=synthetic_markets)
        ).values(
            'id', 'user_id', 'market_id', 'yes_tokens', 'no_tokens',
            'total_staked', 'created_at', 'updated_at'
        )
        
        if not positions.exists():
            self.stdout.write(self.style.WARNING(f'  ⚠ No synthetic positions found, skipping {filepath}'))
            return
        
        fieldnames = [
            'id', 'user_id', 'market_id', 'yes_tokens', 'no_tokens',
            'total_staked', 'created_at', 'updated_at'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for position in positions:
                row = {
                    'id': position['id'],
                    'user_id': position['user_id'],
                    'market_id': position['market_id'],
                    'yes_tokens': float(position['yes_tokens']) if position['yes_tokens'] else 0.0,
                    'no_tokens': float(position['no_tokens']) if position['no_tokens'] else 0.0,
                    'total_staked': float(position['total_staked']) if position['total_staked'] else 0.0,
                    'created_at': position['created_at'].isoformat() if position['created_at'] else '',
                    'updated_at': position['updated_at'].isoformat() if position['updated_at'] else '',
                }
                writer.writerow(row)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Exported {positions.count()} synthetic positions to {filepath}'))

    def _export_outcome_tokens(self, synthetic_markets, output_dir):
        """Export synthetic outcome tokens to CSV"""
        filepath = os.path.join(output_dir, 'outcome_tokens.csv')
        outcome_tokens = OutcomeToken.objects.filter(
            market__in=synthetic_markets
        ).values(
            'id', 'market_id', 'outcome_type', 'price', 'supply', 'created_at', 'updated_at'
        )
        
        if not outcome_tokens.exists():
            self.stdout.write(self.style.WARNING(f'  ⚠ No synthetic outcome tokens found, skipping {filepath}'))
            return
        
        fieldnames = ['id', 'market_id', 'outcome_type', 'price', 'supply', 'created_at', 'updated_at']
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for token in outcome_tokens:
                row = {
                    'id': token['id'],
                    'market_id': token['market_id'],
                    'outcome_type': token['outcome_type'],
                    'price': float(token['price']) if token['price'] else 0.0,
                    'supply': float(token['supply']) if token['supply'] else 0.0,
                    'created_at': token['created_at'].isoformat() if token['created_at'] else '',
                    'updated_at': token['updated_at'].isoformat() if token['updated_at'] else '',
                }
                writer.writerow(row)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Exported {outcome_tokens.count()} synthetic outcome tokens to {filepath}'))

    def _export_price_history(self, synthetic_markets, output_dir):
        """Export synthetic price history to CSV"""
        filepath = os.path.join(output_dir, 'price_history.csv')
        price_history = PriceHistory.objects.filter(
            market__in=synthetic_markets
        ).values(
            'id', 'market_id', 'yes_price', 'no_price', 'timestamp'
        )
        
        if not price_history.exists():
            self.stdout.write(self.style.WARNING(f'  ⚠ No synthetic price history found, skipping {filepath}'))
            return
        
        fieldnames = ['id', 'market_id', 'yes_price', 'no_price', 'timestamp']
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for ph in price_history:
                row = {
                    'id': ph['id'],
                    'market_id': ph['market_id'],
                    'yes_price': float(ph['yes_price']) if ph['yes_price'] else 0.0,
                    'no_price': float(ph['no_price']) if ph['no_price'] else 0.0,
                    'timestamp': ph['timestamp'].isoformat() if ph['timestamp'] else '',
                }
                writer.writerow(row)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Exported {price_history.count()} synthetic price history entries to {filepath}'))

    def _export_liquidity_events(self, synthetic_users, synthetic_markets, output_dir):
        """Export synthetic liquidity events to CSV"""
        filepath = os.path.join(output_dir, 'liquidity_events.csv')
        liquidity_events = LiquidityEvent.objects.filter(
            Q(user__in=synthetic_users) | Q(market__in=synthetic_markets)
        ).values(
            'id', 'market_id', 'user_id', 'event_type', 'amount',
            'onchain_tx_hash', 'onchain_liquidity_id', 'created_at'
        )
        
        if not liquidity_events.exists():
            self.stdout.write(self.style.WARNING(f'  ⚠ No synthetic liquidity events found, skipping {filepath}'))
            return
        
        fieldnames = [
            'id', 'market_id', 'user_id', 'event_type', 'amount',
            'onchain_tx_hash', 'onchain_liquidity_id', 'created_at'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for event in liquidity_events:
                row = {
                    'id': event['id'],
                    'market_id': event['market_id'],
                    'user_id': event['user_id'],
                    'event_type': event['event_type'],
                    'amount': float(event['amount']) if event['amount'] else 0.0,
                    'onchain_tx_hash': event['onchain_tx_hash'] or '',
                    'onchain_liquidity_id': event['onchain_liquidity_id'] or '',
                    'created_at': event['created_at'].isoformat() if event['created_at'] else '',
                }
                writer.writerow(row)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Exported {liquidity_events.count()} synthetic liquidity events to {filepath}'))

    def _export_resolutions(self, synthetic_markets, output_dir):
        """Export synthetic resolutions to CSV"""
        filepath = os.path.join(output_dir, 'resolutions.csv')
        resolutions = Resolution.objects.filter(
            market__in=synthetic_markets
        ).values(
            'id', 'market_id', 'resolved_outcome', 'resolver_id', 'dispute_window',
            'bond_amount', 'onchain_tx_hash', 'created_at'
        )
        
        if not resolutions.exists():
            self.stdout.write(self.style.WARNING(f'  ⚠ No synthetic resolutions found, skipping {filepath}'))
            return
        
        fieldnames = [
            'id', 'market_id', 'resolved_outcome', 'resolver', 'dispute_window',
            'bond_amount', 'onchain_tx_hash', 'created_at'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for resolution in resolutions:
                row = {
                    'id': resolution['id'],
                    'market_id': resolution['market_id'],
                    'resolved_outcome': resolution['resolved_outcome'],
                    'resolver': resolution['resolver_id'] or '',
                    'dispute_window': resolution['dispute_window'].isoformat() if resolution['dispute_window'] else '',
                    'bond_amount': float(resolution['bond_amount']) if resolution['bond_amount'] else 0.0,
                    'onchain_tx_hash': resolution['onchain_tx_hash'] or '',
                    'created_at': resolution['created_at'].isoformat() if resolution['created_at'] else '',
                }
                writer.writerow(row)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Exported {resolutions.count()} synthetic resolutions to {filepath}'))

    def _export_disputes(self, synthetic_users, synthetic_markets, output_dir):
        """Export synthetic disputes to CSV"""
        filepath = os.path.join(output_dir, 'disputes.csv')
        disputes = Dispute.objects.filter(
            Q(user__in=synthetic_users) | Q(market__in=synthetic_markets)
        ).values(
            'id', 'market_id', 'user_id', 'bond_amount', 'status', 'reason',
            'created_at', 'resolved_at'
        )
        
        if not disputes.exists():
            self.stdout.write(self.style.WARNING(f'  ⚠ No synthetic disputes found, skipping {filepath}'))
            return
        
        fieldnames = [
            'id', 'market_id', 'user_id', 'bond_amount', 'status', 'reason',
            'created_at', 'resolved_at'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for dispute in disputes:
                row = {
                    'id': dispute['id'],
                    'market_id': dispute['market_id'],
                    'user_id': dispute['user_id'],
                    'bond_amount': float(dispute['bond_amount']) if dispute['bond_amount'] else 0.0,
                    'status': dispute['status'],
                    'reason': dispute['reason'],
                    'created_at': dispute['created_at'].isoformat() if dispute['created_at'] else '',
                    'resolved_at': dispute['resolved_at'].isoformat() if dispute['resolved_at'] else '',
                }
                writer.writerow(row)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Exported {disputes.count()} synthetic disputes to {filepath}'))

    def _export_onchain_transactions(self, synthetic_users, synthetic_markets, output_dir):
        """Export synthetic onchain transactions to CSV"""
        if not HAS_ONCHAIN_MODELS:
            return
        
        filepath = os.path.join(output_dir, 'onchain_transactions.csv')
        
        # Get synthetic tx hashes from trades, markets, liquidity events, resolutions
        synthetic_tx_hashes = set()
        
        # From trades
        synthetic_tx_hashes.update(
            Trade.objects.filter(
                Q(user__in=synthetic_users) | Q(market__in=synthetic_markets)
            ).exclude(onchain_tx_hash__isnull=True).exclude(onchain_tx_hash='')
            .values_list('onchain_tx_hash', flat=True)
        )
        
        # From markets
        synthetic_tx_hashes.update(
            Market.objects.filter(title__startswith='Synthetic Market')
            .exclude(onchain_tx_hash__isnull=True).exclude(onchain_tx_hash='')
            .values_list('onchain_tx_hash', flat=True)
        )
        
        # From liquidity events
        synthetic_tx_hashes.update(
            LiquidityEvent.objects.filter(
                Q(user__in=synthetic_users) | Q(market__in=synthetic_markets)
            ).exclude(onchain_tx_hash__isnull=True).exclude(onchain_tx_hash='')
            .values_list('onchain_tx_hash', flat=True)
        )
        
        # From resolutions
        synthetic_tx_hashes.update(
            Resolution.objects.filter(market__in=synthetic_markets)
            .exclude(onchain_tx_hash__isnull=True).exclude(onchain_tx_hash='')
            .values_list('onchain_tx_hash', flat=True)
        )
        
        if not synthetic_tx_hashes:
            self.stdout.write(self.style.WARNING(f'  ⚠ No synthetic onchain transactions found, skipping {filepath}'))
            return
        
        transactions = OnchainTransaction.objects.filter(
            tx_hash__in=synthetic_tx_hashes
        ).values(
            'id', 'tx_hash', 'network', 'block_number', 'status',
            'error_message', 'created_at', 'updated_at'
        )
        
        fieldnames = [
            'id', 'tx_hash', 'network', 'block_number', 'status',
            'error_message', 'created_at', 'updated_at'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for tx in transactions:
                row = {
                    'id': tx['id'],
                    'tx_hash': tx['tx_hash'],
                    'network': tx['network'],
                    'block_number': tx['block_number'] or '',
                    'status': tx['status'],
                    'error_message': tx['error_message'] or '',
                    'created_at': tx['created_at'].isoformat() if tx['created_at'] else '',
                    'updated_at': tx['updated_at'].isoformat() if tx['updated_at'] else '',
                }
                writer.writerow(row)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Exported {transactions.count()} synthetic onchain transactions to {filepath}'))

    def _export_onchain_event_logs(self, synthetic_markets, output_dir):
        """Export synthetic onchain event logs to CSV"""
        if not HAS_ONCHAIN_MODELS:
            return
        
        filepath = os.path.join(output_dir, 'onchain_event_logs.csv')
        
        # Get event logs linked to synthetic markets or synthetic transactions
        synthetic_tx_hashes = set()
        
        # From trades
        synthetic_tx_hashes.update(
            Trade.objects.filter(market__in=synthetic_markets)
            .exclude(onchain_tx_hash__isnull=True).exclude(onchain_tx_hash='')
            .values_list('onchain_tx_hash', flat=True)
        )
        
        # From markets
        synthetic_tx_hashes.update(
            Market.objects.filter(title__startswith='Synthetic Market')
            .exclude(onchain_tx_hash__isnull=True).exclude(onchain_tx_hash='')
            .values_list('onchain_tx_hash', flat=True)
        )
        
        # From liquidity events
        synthetic_tx_hashes.update(
            LiquidityEvent.objects.filter(market__in=synthetic_markets)
            .exclude(onchain_tx_hash__isnull=True).exclude(onchain_tx_hash='')
            .values_list('onchain_tx_hash', flat=True)
        )
        
        # From resolutions
        synthetic_tx_hashes.update(
            Resolution.objects.filter(market__in=synthetic_markets)
            .exclude(onchain_tx_hash__isnull=True).exclude(onchain_tx_hash='')
            .values_list('onchain_tx_hash', flat=True)
        )
        
        event_logs = OnchainEventLog.objects.filter(
            Q(market__in=synthetic_markets) | Q(tx_hash__in=synthetic_tx_hashes)
        ).values(
            'id', 'onchain_tx_id', 'event_name', 'tx_hash', 'log_index',
            'market_id', 'user_address', 'payload_json', 'processed_at',
            'duplicate', 'created_at'
        )
        
        if not event_logs.exists():
            self.stdout.write(self.style.WARNING(f'  ⚠ No synthetic onchain event logs found, skipping {filepath}'))
            return
        
        fieldnames = [
            'id', 'onchain_tx_id', 'event_name', 'tx_hash', 'log_index',
            'market_id', 'user_address', 'payload_json', 'processed_at',
            'duplicate', 'created_at'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for log in event_logs:
                row = {
                    'id': log['id'],
                    'onchain_tx_id': log['onchain_tx_id'] or '',
                    'event_name': log['event_name'],
                    'tx_hash': log['tx_hash'],
                    'log_index': log['log_index'],
                    'market_id': log['market_id'] or '',
                    'user_address': log['user_address'] or '',
                    'payload_json': json.dumps(log['payload_json']) if log['payload_json'] else '',
                    'processed_at': log['processed_at'].isoformat() if log['processed_at'] else '',
                    'duplicate': 'True' if log['duplicate'] else 'False',
                    'created_at': log['created_at'].isoformat() if log['created_at'] else '',
                }
                writer.writerow(row)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Exported {event_logs.count()} synthetic onchain event logs to {filepath}'))

