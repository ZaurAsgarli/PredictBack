from django.db import transaction
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
import traceback
import logging

from backend_api.api.trades.models import Trade
from backend_api.api.positions.models import Position
from backend_api.api.markets.models import OutcomeToken, PriceHistory, Market
from backend_api.api.markets.services import MarketService
from backend_api.api.users.models import User

logger = logging.getLogger(__name__)


class TradeExecutionService:
    """Service for executing trades with constant product AMM formula"""
    
    @staticmethod
    @transaction.atomic
    def execute_trade(user, market, outcome_type, amount, side):
        """
        Execute a trade (BUY or SELL) for a market outcome token.
        
        Args:
            user: User instance executing the trade
            market: Market instance
            outcome_type: 'YES' or 'NO'
            amount: Amount to stake (for BUY) or tokens to sell (for SELL)
            side: 'BUY' or 'SELL'
        
        Returns:
            dict: Summary with new balances, prices, and position_size
        
        Raises:
            ValidationError: If trade cannot be executed
        """
        try:
            # Validate inputs
            if user is None:
                raise ValidationError("User cannot be None")
            
            if market is None:
                raise ValidationError("Market cannot be None")
            
            if side not in ['BUY', 'SELL']:
                raise ValidationError(f"Invalid side: {side}. Must be 'BUY' or 'SELL'")
            
            if outcome_type not in ['YES', 'NO']:
                raise ValidationError(f"Invalid outcome_type: {outcome_type}. Must be 'YES' or 'NO'")
            
            if market.status != 'active':
                raise ValidationError(f"Market is not active. Current status: {market.status}")
            
            try:
                amount = Decimal(str(amount))
            except (InvalidOperation, ValueError, TypeError) as e:
                logger.error(f"Invalid amount conversion: {amount}, Error: {str(e)}")
                traceback.print_exc()
                raise ValidationError(f"Invalid amount: {amount}. Must be a valid number")
            
            if amount <= 0:
                raise ValidationError("Amount must be greater than zero")
            
            # Get or create outcome tokens
            try:
                yes_token, _ = OutcomeToken.objects.get_or_create(
                    market=market,
                    outcome_type='YES',
                    defaults={'supply': Decimal('0'), 'price': Decimal('0.5')}
                )
                no_token, _ = OutcomeToken.objects.get_or_create(
                    market=market,
                    outcome_type='NO',
                    defaults={'supply': Decimal('0'), 'price': Decimal('0.5')}
                )
            except Exception as e:
                logger.error(f"Error getting/creating outcome tokens: {str(e)}")
                traceback.print_exc()
                raise ValidationError(f"Failed to get/create outcome tokens: {str(e)}")
            
            # Get target and opposite tokens
            target_token = yes_token if outcome_type == 'YES' else no_token
            opposite_token = no_token if outcome_type == 'YES' else yes_token
            
            # Get or create position
            try:
                position, _ = Position.objects.get_or_create(
                    user=user,
                    market=market,
                    defaults={
                        'yes_tokens': Decimal('0'),
                        'no_tokens': Decimal('0'),
                        'total_staked': Decimal('0')
                    }
                )
            except Exception as e:
                logger.error(f"Error getting/creating position: {str(e)}")
                traceback.print_exc()
                raise ValidationError(f"Failed to get/create position: {str(e)}")
            
            # Store initial values for price calculation
            try:
                initial_yes_supply = yes_token.supply
                initial_no_supply = no_token.supply
            except Exception as e:
                logger.error(f"Error reading token supplies: {str(e)}")
                traceback.print_exc()
                raise ValidationError(f"Failed to read token supplies: {str(e)}")
            
            # Initialize trade result variables
            tokens_received = Decimal('0')
            amount_received = Decimal('0')
            price_at_execution = Decimal('0.5')
            
            # Execute trade based on side
            try:
                if side == 'BUY':
                    tokens_received, price_at_execution = TradeExecutionService._execute_buy(
                        target_token, opposite_token, amount
                    )
                    
                    # Update position for BUY
                    if outcome_type == 'YES':
                        position.yes_tokens += tokens_received
                    else:
                        position.no_tokens += tokens_received
                    position.total_staked += amount
                    
                else:  # SELL
                    # Validate user has enough tokens
                    user_tokens = position.yes_tokens if outcome_type == 'YES' else position.no_tokens
                    if user_tokens < amount:
                        raise ValidationError(f"Insufficient {outcome_type} tokens. Available: {user_tokens}, Required: {amount}")
                    
                    amount_received, price_at_execution = TradeExecutionService._execute_sell(
                        target_token, opposite_token, amount
                    )
                    
                    # Update position for SELL
                    if outcome_type == 'YES':
                        position.yes_tokens -= amount
                    else:
                        position.no_tokens -= amount
                    position.total_staked -= amount_received
            except ValidationError:
                raise
            except Exception as e:
                logger.error(f"Error executing trade ({side}): {str(e)}")
                traceback.print_exc()
                raise ValidationError(f"Trade execution failed: {str(e)}")
            
            # Save position
            try:
                position.save()
            except Exception as e:
                logger.error(f"Error saving position: {str(e)}")
                traceback.print_exc()
                raise ValidationError(f"Failed to save position: {str(e)}")
            
            # Update token prices using constant product formula
            try:
                TradeExecutionService._update_token_prices(yes_token, no_token)
            except Exception as e:
                logger.error(f"Error updating token prices: {str(e)}")
                traceback.print_exc()
                raise ValidationError(f"Failed to update token prices: {str(e)}")
            
            # Update market liquidity pool
            try:
                market.liquidity_pool = yes_token.supply + no_token.supply
                market.save()
            except Exception as e:
                logger.error(f"Error updating market liquidity: {str(e)}")
                traceback.print_exc()
                raise ValidationError(f"Failed to update market liquidity: {str(e)}")
            
            # Update market status (check if closed due to liquidity or expiration)
            try:
                MarketService.update_status(market)
            except Exception as e:
                logger.error(f"Error updating market status: {str(e)}")
                traceback.print_exc()
                # Don't fail the trade if status update fails, just log it
                logger.warning(f"Market status update failed but trade will continue: {str(e)}")
            
            # Create trade record
            try:
                trade = Trade.objects.create(
                    user=user,
                    market=market,
                    outcome_type=outcome_type,
                    trade_type=side.lower(),
                    amount_staked=amount if side == 'BUY' else amount_received,
                    tokens_amount=tokens_received if side == 'BUY' else amount,
                    price_at_execution=price_at_execution
                )
            except Exception as e:
                logger.error(f"Error creating trade record: {str(e)}")
                traceback.print_exc()
                raise ValidationError(f"Failed to create trade record: {str(e)}")
            
            # Create price history entry
            try:
                PriceHistory.objects.create(
                    market=market,
                    yes_price=yes_token.price,
                    no_price=no_token.price
                )
            except Exception as e:
                logger.error(f"Error creating price history: {str(e)}")
                traceback.print_exc()
                # Don't fail the trade if price history fails, just log it
                logger.warning(f"Price history creation failed but trade will continue: {str(e)}")
            
            # Prepare summary
            try:
                summary = {
                    'trade_id': trade.id,
                    'new_balances': {
                        'yes_tokens': float(position.yes_tokens),
                        'no_tokens': float(position.no_tokens),
                        'total_staked': float(position.total_staked)
                    },
                    'prices': {
                        'yes_price': float(yes_token.price),
                        'no_price': float(no_token.price)
                    },
                    'position_size': {
                        'yes_tokens': float(position.yes_tokens),
                        'no_tokens': float(position.no_tokens)
                    }
                }
            except Exception as e:
                logger.error(f"Error preparing summary: {str(e)}")
                traceback.print_exc()
                raise ValidationError(f"Failed to prepare trade summary: {str(e)}")
            
            return summary
            
        except ValidationError:
            # Re-raise ValidationError as-is
            raise
        except Exception as e:
            # Catch any other unexpected errors
            logger.error(f"Unexpected error in execute_trade: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            traceback.print_exc()
            raise ValidationError(f"Unexpected error during trade execution: {str(e)}")
    
    @staticmethod
    def _execute_buy(target_token, opposite_token, amount_staked):
        """
        Execute a BUY trade using constant product formula.
        
        Constant product: k = yes_supply * no_supply
        When buying target tokens:
        - Add amount_staked to target token supply
        - Calculate new opposite token supply to maintain k
        - Tokens received = initial_opposite_supply - new_opposite_supply
        
        Args:
            target_token: Token being bought
            opposite_token: The other token in the pair
            amount_staked: Amount to stake
        
        Returns:
            tuple: (tokens_received, price_at_execution)
        
        Raises:
            ValidationError: If calculation fails
        """
        try:
            if target_token is None or opposite_token is None:
                raise ValidationError("Token instances cannot be None")
            
            if amount_staked is None or amount_staked <= 0:
                raise ValidationError(f"Invalid amount_staked: {amount_staked}")
            
            initial_target_supply = target_token.supply or Decimal('0')
            initial_opposite_supply = opposite_token.supply or Decimal('0')
            
            # Handle initial liquidity (k = 0)
            if initial_target_supply == 0 and initial_opposite_supply == 0:
                # Initialize with equal liquidity
                target_token.supply = amount_staked
                opposite_token.supply = amount_staked
                tokens_received = amount_staked
                price_at_execution = Decimal('0.5')
            else:
                # Calculate constant product
                k = initial_target_supply * initial_opposite_supply
                
                # New target supply after adding staked amount
                new_target_supply = initial_target_supply + amount_staked
                
                # Calculate new opposite supply to maintain constant product
                if new_target_supply > 0:
                    new_opposite_supply = k / new_target_supply
                else:
                    logger.error(f"Division by zero: new_target_supply={new_target_supply}")
                    raise ValidationError("Invalid target supply calculation")
                
                # Tokens received is the difference in opposite supply
                tokens_received = initial_opposite_supply - new_opposite_supply
                
                # Ensure tokens_received is positive
                if tokens_received < 0:
                    tokens_received = Decimal('0')
                
                # Update supplies
                target_token.supply = new_target_supply
                opposite_token.supply = new_opposite_supply
                
                # Calculate price at execution (before update)
                total_supply = initial_target_supply + initial_opposite_supply
                if total_supply > 0:
                    price_at_execution = initial_target_supply / total_supply
                else:
                    price_at_execution = Decimal('0.5')
            
            # Save tokens
            target_token.save()
            opposite_token.save()
            
            return tokens_received, price_at_execution
            
        except ValidationError:
            raise
        except ZeroDivisionError as e:
            logger.error(f"Division by zero in _execute_buy: {str(e)}")
            traceback.print_exc()
            raise ValidationError(f"Calculation error: division by zero")
        except Exception as e:
            logger.error(f"Error in _execute_buy: {str(e)}")
            traceback.print_exc()
            raise ValidationError(f"Buy execution failed: {str(e)}")
    
    @staticmethod
    def _execute_sell(target_token, opposite_token, tokens_to_sell):
        """
        Execute a SELL trade using constant product formula.
        
        Constant product: k = yes_supply * no_supply
        When selling target tokens:
        - Remove tokens_to_sell from target token supply
        - Calculate new opposite token supply to maintain k
        - Amount received = new_opposite_supply - initial_opposite_supply
        
        Args:
            target_token: Token being sold
            opposite_token: The other token in the pair
            tokens_to_sell: Number of tokens to sell
        
        Returns:
            tuple: (amount_received, price_at_execution)
        
        Raises:
            ValidationError: If calculation fails
        """
        try:
            if target_token is None or opposite_token is None:
                raise ValidationError("Token instances cannot be None")
            
            if tokens_to_sell is None or tokens_to_sell <= 0:
                raise ValidationError(f"Invalid tokens_to_sell: {tokens_to_sell}")
            
            initial_target_supply = target_token.supply or Decimal('0')
            initial_opposite_supply = opposite_token.supply or Decimal('0')
            
            # Calculate price at execution (before update)
            total_supply = initial_target_supply + initial_opposite_supply
            if total_supply > 0:
                price_at_execution = initial_target_supply / total_supply
            else:
                price_at_execution = Decimal('0.5')
            
            # Calculate constant product
            k = initial_target_supply * initial_opposite_supply
            
            # New target supply after removing tokens
            new_target_supply = initial_target_supply - tokens_to_sell
            
            # Prevent negative supply
            if new_target_supply < 0:
                new_target_supply = Decimal('0')
            
            # Calculate new opposite supply to maintain constant product
            if new_target_supply > 0:
                new_opposite_supply = k / new_target_supply
            else:
                new_opposite_supply = Decimal('0')
            
            # Amount received is the difference in opposite supply
            amount_received = new_opposite_supply - initial_opposite_supply
            
            # Ensure amount_received is positive
            if amount_received < 0:
                amount_received = Decimal('0')
            
            # Update supplies
            target_token.supply = new_target_supply
            opposite_token.supply = new_opposite_supply
            
            # Save tokens
            target_token.save()
            opposite_token.save()
            
            return amount_received, price_at_execution
            
        except ValidationError:
            raise
        except ZeroDivisionError as e:
            logger.error(f"Division by zero in _execute_sell: {str(e)}")
            traceback.print_exc()
            raise ValidationError(f"Calculation error: division by zero")
        except Exception as e:
            logger.error(f"Error in _execute_sell: {str(e)}")
            traceback.print_exc()
            raise ValidationError(f"Sell execution failed: {str(e)}")
    
    @staticmethod
    def _update_token_prices(yes_token, no_token):
        """
        Update token prices based on current supply using constant product formula.
        
        Price is calculated as: token_supply / total_supply
        
        Args:
            yes_token: YES outcome token
            no_token: NO outcome token
        
        Raises:
            ValidationError: If calculation fails
        """
        try:
            if yes_token is None or no_token is None:
                raise ValidationError("Token instances cannot be None")
            
            yes_supply = yes_token.supply or Decimal('0')
            no_supply = no_token.supply or Decimal('0')
            total_supply = yes_supply + no_supply
            
            if total_supply > 0:
                yes_token.price = yes_supply / total_supply
                no_token.price = no_supply / total_supply
            else:
                yes_token.price = Decimal('0.5')
                no_token.price = Decimal('0.5')
            
            yes_token.save()
            no_token.save()
            
        except ZeroDivisionError as e:
            logger.error(f"Division by zero in _update_token_prices: {str(e)}")
            traceback.print_exc()
            raise ValidationError(f"Price calculation error: division by zero")
        except Exception as e:
            logger.error(f"Error in _update_token_prices: {str(e)}")
            traceback.print_exc()
            raise ValidationError(f"Failed to update token prices: {str(e)}")

