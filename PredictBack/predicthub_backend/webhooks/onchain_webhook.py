"""
On-chain webhook handler for processing blockchain events.
Handles events: TradeExecuted, LiquidityAdded, LiquidityRemoved, DisputeOpened, MarketResolved
"""
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from decimal import Decimal
import json
import logging

from indexer.models import OnchainTransaction, OnchainEventLog
from markets.models import Market, Resolution
from markets.services import MarketService
from users.models import User
from liquidity.models import LiquidityEvent
from disputes.models import Dispute
from trades.services import TradeExecutionService
from utils.serializer import success, error

logger = logging.getLogger(__name__)


def get_or_create_user_by_address(wallet_address):
    """
    Get or create a User by wallet address.
    Creates a user with wallet-based username/email if not exists.
    
    Args:
        wallet_address: Ethereum wallet address (hex string)
    
    Returns:
        User: User instance
    """
    if not wallet_address:
        return None
    
    # Normalize address (lowercase)
    wallet_address = wallet_address.lower()
    
    # Try to find user by a pattern (if you have wallet_address field)
    # For now, we'll create users with wallet-based identifiers
    username = f"wallet_{wallet_address[:16]}"
    email = f"{wallet_address}@wallet.local"
    
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'username': username,
            'email': email,
        }
    )
    
    if created:
        logger.info(f"Created new user for wallet address: {wallet_address[:10]}...")
    
    return user


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def onchain_webhook(request):
    """
    Handle on-chain webhook events from blockchain indexer.
    
    Expected POST data:
    {
        "tx_hash": "...",
        "event_name": "TradeExecuted" | "LiquidityAdded" | "LiquidityRemoved" | "DisputeOpened" | "MarketResolved",
        "payload": {
            // Event-specific payload
        }
    }
    
    Returns:
        JSON: { "success": true }
    """
    try:
        # Parse request data
        if isinstance(request.data, dict):
            data = request.data
        else:
            data = json.loads(request.body or "{}")
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Invalid JSON in webhook request: {e}")
        return error('Invalid JSON', status.HTTP_400_BAD_REQUEST)
    
    # Validate required fields
    tx_hash = data.get('tx_hash')
    event_name = data.get('event_name')
    payload = data.get('payload', {})
    
    if not tx_hash:
        return error('tx_hash is required', status.HTTP_400_BAD_REQUEST)
    
    if not event_name:
        return error('event_name is required', status.HTTP_400_BAD_REQUEST)
    
    # Extract optional fields
    log_index = data.get('log_index', 0)
    block_number = data.get('block_number')
    user_address = payload.get('user_address') or payload.get('user') or data.get('user_address', '')
    market_id = payload.get('market_id') or data.get('market_id')
    
    try:
        with transaction.atomic():
            # 1. Create or fetch OnchainTransaction
            onchain_tx, created_tx = OnchainTransaction.objects.get_or_create(
                tx_hash=tx_hash,
                defaults={
                    'network': data.get('network', 'sepolia'),
                    'block_number': block_number,
                    'status': 'SUCCESS' if event_name else 'PENDING',
                }
            )
            
            # Update block number if provided and transaction exists
            if not created_tx and block_number is not None:
                onchain_tx.block_number = block_number
                onchain_tx.status = 'SUCCESS'
                onchain_tx.save(update_fields=['block_number', 'status', 'updated_at'])
            
            # 2. Create OnchainEventLog
            event_log, created_event = OnchainEventLog.objects.get_or_create(
                tx_hash=tx_hash,
                log_index=log_index,
                defaults={
                    'onchain_tx': onchain_tx,
                    'event_name': event_name,
                    'user_address': user_address,
                    'payload_json': payload,
                }
            )
            
            # Mark as duplicate if already exists
            if not created_event:
                event_log.duplicate = True
                # If already processed, skip processing
                if event_log.processed_at:
                    logger.info(f"Event {event_name} already processed for tx {tx_hash[:10]}...")
                    return Response({'success': True, 'duplicate': True})
            
            # Update event log with latest data
            event_log.onchain_tx = onchain_tx
            event_log.event_name = event_name
            event_log.user_address = user_address
            event_log.payload_json = payload
            
            # Link market if provided
            if market_id:
                try:
                    market = Market.objects.get(pk=market_id)
                    event_log.market = market
                except Market.DoesNotExist:
                    logger.warning(f"Market {market_id} not found for event {event_name}")
            
            event_log.save()
            
            # 3. Detect event type and process
            try:
                market_id_for_status_update = None
                
                if event_name == 'TradeExecuted':
                    process_trade_executed(event_log, payload)
                    market_id_for_status_update = payload.get('market_id') or (event_log.market.id if event_log.market else None)
                elif event_name == 'LiquidityAdded':
                    process_liquidity_added(event_log, payload)
                    market_id_for_status_update = payload.get('market_id') or (event_log.market.id if event_log.market else None)
                elif event_name == 'LiquidityRemoved':
                    process_liquidity_removed(event_log, payload)
                    market_id_for_status_update = payload.get('market_id') or (event_log.market.id if event_log.market else None)
                elif event_name == 'DisputeOpened':
                    process_dispute_opened(event_log, payload)
                elif event_name == 'MarketResolved':
                    process_market_resolved(event_log, payload)
                    market_id_for_status_update = payload.get('market_id') or (event_log.market.id if event_log.market else None)
                else:
                    logger.warning(f"Unknown event type: {event_name}")
                
                # Update market status after events that affect market state
                if market_id_for_status_update:
                    try:
                        market = Market.objects.get(pk=market_id_for_status_update)
                        MarketService.update_status(market)
                    except Market.DoesNotExist:
                        logger.warning(f"Market {market_id_for_status_update} not found for status update")
                
                # Mark as processed
                event_log.processed_at = timezone.now()
                event_log.save(update_fields=['processed_at'])
                
            except Exception as e:
                logger.error(f"Error processing event {event_name}: {str(e)}", exc_info=True)
                event_log.processed_at = None
                event_log.save(update_fields=['processed_at'])
                # Don't fail the webhook, just log the error
                # The event can be retried later
            
    except Exception as e:
        logger.error(f"Error in webhook handler: {str(e)}", exc_info=True)
        return error(f'Internal server error: {str(e)}', status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return success()


def process_trade_executed(event_log, payload):
    """
    Process TradeExecuted event.
    Calls TradeExecutionService with payload values.
    
    Expected payload:
    {
        "user_address": "0x...",
        "market_id": 1,
        "outcome_type": "YES" | "NO",
        "side": "BUY" | "SELL",
        "amount": "100.00"  # Decimal as string
    }
    """
    user_address = payload.get('user_address') or event_log.user_address
    market_id = payload.get('market_id')
    outcome_type = payload.get('outcome_type')
    side = payload.get('side')  # BUY or SELL
    amount = payload.get('amount') or payload.get('amount_staked') or payload.get('tokens_amount')
    
    if not all([user_address, market_id, outcome_type, side, amount]):
        raise ValidationError(f"Missing required fields in TradeExecuted payload: {payload}")
    
    # Get or create user
    user = get_or_create_user_by_address(user_address)
    if not user:
        raise ValidationError(f"Could not create user for address: {user_address}")
    
    # Get market
    try:
        market = Market.objects.get(pk=market_id)
    except Market.DoesNotExist:
        raise ValidationError(f"Market {market_id} not found")
    
    # Validate outcome_type
    if outcome_type not in ['YES', 'NO']:
        raise ValidationError(f"Invalid outcome_type: {outcome_type}")
    
    # Validate side
    if side.upper() not in ['BUY', 'SELL']:
        raise ValidationError(f"Invalid side: {side}")
    
    # Convert amount to Decimal
    try:
        amount = Decimal(str(amount))
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid amount: {amount}")
    
    # Execute trade
    TradeExecutionService.execute_trade(
        user=user,
        market=market,
        outcome_type=outcome_type,
        amount=amount,
        side=side.upper()
    )
    
    logger.info(f"TradeExecuted processed: {side} {outcome_type} {amount} for market {market_id}")


def process_liquidity_added(event_log, payload):
    """
    Process LiquidityAdded event.
    Creates LiquidityEvent record.
    
    Expected payload:
    {
        "user_address": "0x...",
        "market_id": 1,
        "amount": "1000.00"
    }
    """
    user_address = payload.get('user_address') or event_log.user_address
    market_id = payload.get('market_id')
    amount = payload.get('amount')
    
    if not all([user_address, market_id, amount]):
        raise ValidationError(f"Missing required fields in LiquidityAdded payload: {payload}")
    
    # Get or create user
    user = get_or_create_user_by_address(user_address)
    if not user:
        raise ValidationError(f"Could not create user for address: {user_address}")
    
    # Get market
    try:
        market = Market.objects.get(pk=market_id)
    except Market.DoesNotExist:
        raise ValidationError(f"Market {market_id} not found")
    
    # Convert amount to Decimal
    try:
        amount = Decimal(str(amount))
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid amount: {amount}")
    
    # Create liquidity event
    LiquidityEvent.objects.create(
        market=market,
        user=user,
        event_type='add',
        amount=amount
    )
    
    # Update market liquidity pool
    market.liquidity_pool += amount
    market.save(update_fields=['liquidity_pool'])
    
    logger.info(f"LiquidityAdded processed: {amount} for market {market_id}")


def process_liquidity_removed(event_log, payload):
    """
    Process LiquidityRemoved event.
    Creates LiquidityEvent record.
    
    Expected payload:
    {
        "user_address": "0x...",
        "market_id": 1,
        "amount": "500.00"
    }
    """
    user_address = payload.get('user_address') or event_log.user_address
    market_id = payload.get('market_id')
    amount = payload.get('amount')
    
    if not all([user_address, market_id, amount]):
        raise ValidationError(f"Missing required fields in LiquidityRemoved payload: {payload}")
    
    # Get or create user
    user = get_or_create_user_by_address(user_address)
    if not user:
        raise ValidationError(f"Could not create user for address: {user_address}")
    
    # Get market
    try:
        market = Market.objects.get(pk=market_id)
    except Market.DoesNotExist:
        raise ValidationError(f"Market {market_id} not found")
    
    # Convert amount to Decimal
    try:
        amount = Decimal(str(amount))
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid amount: {amount}")
    
    # Create liquidity event
    LiquidityEvent.objects.create(
        market=market,
        user=user,
        event_type='remove',
        amount=amount
    )
    
    # Update market liquidity pool
    market.liquidity_pool = max(Decimal('0'), market.liquidity_pool - amount)
    market.save(update_fields=['liquidity_pool'])
    
    logger.info(f"LiquidityRemoved processed: {amount} for market {market_id}")


def process_dispute_opened(event_log, payload):
    """
    Process DisputeOpened event.
    Creates Dispute record.
    
    Expected payload:
    {
        "user_address": "0x...",
        "market_id": 1,
        "bond_amount": "100.00",
        "reason": "Market resolution is incorrect"
    }
    """
    user_address = payload.get('user_address') or event_log.user_address
    market_id = payload.get('market_id')
    bond_amount = payload.get('bond_amount')
    reason = payload.get('reason', 'Dispute opened via on-chain event')
    
    if not all([user_address, market_id, bond_amount]):
        raise ValidationError(f"Missing required fields in DisputeOpened payload: {payload}")
    
    # Get or create user
    user = get_or_create_user_by_address(user_address)
    if not user:
        raise ValidationError(f"Could not create user for address: {user_address}")
    
    # Get market
    try:
        market = Market.objects.get(pk=market_id)
    except Market.DoesNotExist:
        raise ValidationError(f"Market {market_id} not found")
    
    # Convert bond_amount to Decimal
    try:
        bond_amount = Decimal(str(bond_amount))
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid bond_amount: {bond_amount}")
    
    # Create dispute
    Dispute.objects.create(
        market=market,
        user=user,
        bond_amount=bond_amount,
        status='pending',
        reason=reason
    )
    
    logger.info(f"DisputeOpened processed for market {market_id} by {user_address[:10]}...")


def process_market_resolved(event_log, payload):
    """
    Process MarketResolved event.
    Creates or updates Resolution record and updates Market status.
    
    Expected payload:
    {
        "market_id": 1,
        "resolved_outcome": "YES" | "NO",
        "resolver_address": "0x...",
        "dispute_window": "2024-12-31T23:59:59Z",  # ISO format
        "bond_amount": "100.00"
    }
    """
    market_id = payload.get('market_id')
    resolved_outcome = payload.get('resolved_outcome')
    resolver_address = payload.get('resolver_address') or payload.get('resolver')
    dispute_window = payload.get('dispute_window')
    bond_amount = payload.get('bond_amount', 100.0)
    
    if not all([market_id, resolved_outcome]):
        raise ValidationError(f"Missing required fields in MarketResolved payload: {payload}")
    
    # Get market
    try:
        market = Market.objects.get(pk=market_id)
    except Market.DoesNotExist:
        raise ValidationError(f"Market {market_id} not found")
    
    # Validate resolved_outcome
    if resolved_outcome not in ['YES', 'NO']:
        raise ValidationError(f"Invalid resolved_outcome: {resolved_outcome}")
    
    # Get resolver user if address provided
    resolver = None
    if resolver_address:
        resolver = get_or_create_user_by_address(resolver_address)
    
    # Convert bond_amount to Decimal
    try:
        bond_amount = Decimal(str(bond_amount))
    except (ValueError, TypeError):
        bond_amount = Decimal('100.0')
    
    # Parse dispute_window if provided
    dispute_window_dt = None
    if dispute_window:
        try:
            from django.utils.dateparse import parse_datetime
            dispute_window_dt = parse_datetime(dispute_window)
        except (ValueError, TypeError):
            # Default to 7 days from now
            from datetime import timedelta
            dispute_window_dt = timezone.now() + timedelta(days=7)
    
    if not dispute_window_dt:
        from datetime import timedelta
        dispute_window_dt = timezone.now() + timedelta(days=7)
    
    # Create or update resolution
    resolution, created = Resolution.objects.get_or_create(
        market=market,
        defaults={
            'resolved_outcome': resolved_outcome,
            'resolver': resolver,
            'dispute_window': dispute_window_dt,
            'bond_amount': bond_amount,
        }
    )
    
    if not created:
        resolution.resolved_outcome = resolved_outcome
        resolution.resolver = resolver
        resolution.dispute_window = dispute_window_dt
        resolution.bond_amount = bond_amount
        resolution.save()
    
    # Update market resolution_outcome (status will be updated by MarketService in webhook handler)
    market.resolution_outcome = resolved_outcome
    market.save(update_fields=['resolution_outcome'])
    
    logger.info(f"MarketResolved processed: market {market_id} -> {resolved_outcome}")

