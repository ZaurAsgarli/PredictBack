"""
Event processor for mapping blockchain events to Django models
"""
import json
import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from web3.types import LogReceipt

from markets.models import Market, Resolution, MarketCategory
from trades.models import Trade
from liquidity.models import LiquidityEvent
from users.models import User
from .models import OnchainTransaction, OnchainEventLog
from utils.contracts import get_contract_service
from webhooks.onchain_webhook import get_or_create_user_by_address
from utils.logging import get_onchain_loggers

logger = logging.getLogger(__name__)


class EventProcessor:
    """Processes blockchain events and maps them to Django models with structured logging"""
    
    def __init__(self):
        self.contract_service = get_contract_service()
        self.logger = logging.getLogger(f"{__name__}.EventProcessor")
        # Setup structured JSON loggers
        self.onchain_loggers = get_onchain_loggers()
    
    def process_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single event and create/update Django models
        
        Returns:
            Dict with 'success', 'duplicate', 'error' keys
        """
        event_name = event_data.get('event')
        args = event_data.get('args', {})
        tx_hash = event_data.get('transactionHash', '')
        log_index = event_data.get('logIndex', 0)
        block_number = event_data.get('blockNumber', 0)
        
        log_data = {
            'event_name': event_name,
            'tx_hash': tx_hash,
            'log_index': log_index,
            'block_number': block_number,
            'timestamp': timezone.now().isoformat(),
        }
        
        # Check for duplicates (idempotent)
        if OnchainEventLog.objects.filter(tx_hash=tx_hash, log_index=log_index).exists():
            self.logger.info(f"Duplicate event suppressed: {tx_hash}:{log_index}", extra=log_data)
            # Log duplicate to structured logger
            self.onchain_loggers['duplicates'].info(
                f"Duplicate event suppressed",
                extra={
                    'event_name': event_name,
                    'tx_hash': tx_hash,
                    'log_index': log_index,
                    'block_number': block_number,
                    'duplicate': True,
                }
            )
            return {'success': False, 'duplicate': True, 'error': None}
        
        try:
            with transaction.atomic():
                # Get or create transaction
                onchain_tx, tx_created = OnchainTransaction.objects.get_or_create(
                    tx_hash=tx_hash,
                    defaults={
                        'network': 'base-sepolia',
                        'block_number': block_number,
                        'status': 'SUCCESS',
                    }
                )
                
                if not tx_created and block_number:
                    onchain_tx.block_number = block_number
                    onchain_tx.status = 'SUCCESS'
                    onchain_tx.save()
                
                # Create event log entry
                event_log = OnchainEventLog.objects.create(
                    onchain_tx=onchain_tx,
                    event_name=event_name,
                    tx_hash=tx_hash,
                    log_index=log_index,
                    payload_json=args,
                    user_address=args.get('user', args.get('creator', '')),
                )
                
                # Process based on event type
                processing_result = None
                if event_name == 'MarketCreated':
                    processing_result = self._process_market_created(event_log, args)
                elif event_name == 'TradeExecuted':
                    processing_result = self._process_trade_executed(event_log, args)
                elif event_name == 'LiquidityAdded':
                    processing_result = self._process_liquidity_added(event_log, args)
                elif event_name == 'MarketResolved':
                    processing_result = self._process_market_resolved(event_log, args)
                else:
                    self.logger.warning(f"Unknown event type: {event_name}", extra=log_data)
                
                event_log.processed_at = timezone.now()
                event_log.save()
                
                log_data.update({
                    'processed': True,
                    'market_id': processing_result.get('market_id') if processing_result else None,
                })
                self.logger.info(f"Processed {event_name} event", extra=log_data)
                
                # Log successful event to structured logger
                market_id = processing_result.get('market_id') if processing_result else None
                user_address = args.get('user', args.get('creator', ''))
                self.onchain_loggers['events'].info(
                    f"Processed {event_name} event",
                    extra={
                        'event_name': event_name,
                        'tx_hash': tx_hash,
                        'log_index': log_index,
                        'block_number': block_number,
                        'market_id': market_id,
                        'user_address': user_address,
                        'success': True,
                    }
                )
                
                return {'success': True, 'duplicate': False, 'error': None, 'data': processing_result}
                
        except Exception as e:
            log_data['error'] = str(e)
            self.logger.error(f"Error processing event {event_name}: {e}", extra=log_data, exc_info=True)
            
            # Log error to structured logger
            self.onchain_loggers['errors'].error(
                f"Error processing {event_name} event: {str(e)}",
                extra={
                    'event_name': event_name,
                    'tx_hash': tx_hash,
                    'log_index': log_index,
                    'block_number': block_number,
                    'error': str(e),
                    'success': False,
                },
                exc_info=True
            )
            
            # Mark transaction as failed
            try:
                OnchainTransaction.objects.filter(tx_hash=tx_hash).update(
                    status='FAILED',
                    error_message=str(e)
                )
            except:
                pass
            
            return {'success': False, 'duplicate': False, 'error': str(e)}
    
    def _process_market_created(self, event_log: OnchainEventLog, args: Dict[str, Any]) -> Dict[str, Any]:
        """Process MarketCreated event"""
        market_id = args.get('marketId')
        creator_address = args.get('creator', '')
        end_time = args.get('endTime', 0)
        
        if not market_id:
            raise ValueError("marketId is required")
        
        # Convert timestamp
        from datetime import datetime
        ends_at = datetime.fromtimestamp(end_time, tz=timezone.utc)
        
        # Get or create default category
        category, _ = MarketCategory.objects.get_or_create(
            slug='general',
            defaults={'name': 'General', 'description': 'General prediction markets'}
        )
        
        # Create market
        market, created = Market.objects.get_or_create(
            onchain_market_id=market_id,
            defaults={
                'title': f"Market #{market_id}",
                'description': f"On-chain market #{market_id}",
                'category': category,
                'status': 'active',
                'ends_at': ends_at,
                'created_by': None,  # User mapping needed
                'onchain_tx_hash': event_log.tx_hash,
            }
        )
        
        if not created:
            market.onchain_tx_hash = event_log.tx_hash
            market.save()
        
        event_log.market = market
        event_log.save()
        
        return {'market_id': market.id, 'onchain_market_id': market_id, 'created': created}
    
    def _process_trade_executed(self, event_log: OnchainEventLog, args: Dict[str, Any]) -> Dict[str, Any]:
        """Process TradeExecuted event"""
        market_id = args.get('marketId')
        user_address = args.get('user', '')
        outcome = args.get('outcome', False)
        amount = args.get('amount', 0)
        trade_id = args.get('tradeId', 0)
        
        try:
            market = Market.objects.get(onchain_market_id=market_id)
        except Market.DoesNotExist:
            raise ValueError(f"Market {market_id} not found")
        
        # Convert wei to decimal
        amount_decimal = Decimal(amount) / Decimal(10**18)
        
        # Get or create user by wallet address
        user = get_or_create_user_by_address(user_address)
        
        # Create trade
        trade = Trade.objects.create(
            market=market,
            user=user,
            outcome_type='YES' if outcome else 'NO',
            trade_type='buy',
            amount_staked=amount_decimal,
            tokens_amount=amount_decimal,  # Simplified - should calculate from AMM
            price_at_execution=Decimal('0.5'),  # Should calculate from AMM
            onchain_tx_hash=event_log.tx_hash,
            onchain_trade_id=trade_id,
        )
        
        event_log.market = market
        event_log.save()
        
        return {'trade_id': trade.id, 'onchain_trade_id': trade_id, 'market_id': market.id}
    
    def _process_liquidity_added(self, event_log: OnchainEventLog, args: Dict[str, Any]) -> Dict[str, Any]:
        """Process LiquidityAdded event"""
        market_id = args.get('marketId')
        user_address = args.get('user', '')
        amount = args.get('amount', 0)
        liquidity_id = args.get('liquidityId', 0)
        
        try:
            market = Market.objects.get(onchain_market_id=market_id)
        except Market.DoesNotExist:
            raise ValueError(f"Market {market_id} not found")
        
        # Convert wei to decimal
        amount_decimal = Decimal(amount) / Decimal(10**18)
        
        # Get or create user by wallet address
        user = get_or_create_user_by_address(user_address)
        
        # Create liquidity event
        liquidity_event = LiquidityEvent.objects.create(
            market=market,
            user=user,
            event_type='add',
            amount=amount_decimal,
            onchain_tx_hash=event_log.tx_hash,
            onchain_liquidity_id=liquidity_id,
        )
        
        # Update market liquidity pool
        market.liquidity_pool += amount_decimal
        market.save()
        
        event_log.market = market
        event_log.save()
        
        return {
            'liquidity_event_id': liquidity_event.id,
            'onchain_liquidity_id': liquidity_id,
            'market_id': market.id
        }
    
    def _process_market_resolved(self, event_log: OnchainEventLog, args: Dict[str, Any]) -> Dict[str, Any]:
        """Process MarketResolved event"""
        market_id = args.get('marketId')
        outcome = args.get('outcome', False)
        
        try:
            market = Market.objects.get(onchain_market_id=market_id)
        except Market.DoesNotExist:
            raise ValueError(f"Market {market_id} not found")
        
        # Update market status
        market.status = 'resolved'
        market.resolution_outcome = 'YES' if outcome else 'NO'
        market.save()
        
        # Create resolution
        resolution, created = Resolution.objects.get_or_create(
            market=market,
            defaults={
                'resolved_outcome': 'YES' if outcome else 'NO',
                'resolver': None,
                'dispute_window': timezone.now() + timezone.timedelta(hours=48),
                'onchain_tx_hash': event_log.tx_hash,
            }
        )
        
        if not created:
            resolution.onchain_tx_hash = event_log.tx_hash
            resolution.save()
        
        event_log.market = market
        event_log.save()
        
        return {'resolution_id': resolution.id, 'market_id': market.id, 'outcome': 'YES' if outcome else 'NO'}
