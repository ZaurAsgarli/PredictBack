from django.db import transaction
from decimal import Decimal
from django.core.exceptions import ValidationError

from positions.models import Position
from markets.models import Market, OutcomeToken
from users.models import User


class PositionService:
    """Service for managing user positions in prediction markets"""
    
    @staticmethod
    @transaction.atomic
    def update_position(user, market, outcome_type, amount, side, execution_price=None):
        """
        Update a user's position for a market based on trade execution.
        
        Args:
            user: User instance
            market: Market instance
            outcome_type: 'YES' or 'NO'
            amount: Amount of tokens (for BUY) or tokens to sell (for SELL)
            side: 'BUY' or 'SELL'
            execution_price: Optional price at which trade was executed
        
        Returns:
            Position: Updated Position object
        
        Raises:
            ValidationError: If trade cannot be executed (e.g., insufficient tokens)
        """
        # Validate inputs
        if side not in ['BUY', 'SELL']:
            raise ValidationError(f"Invalid side: {side}. Must be 'BUY' or 'SELL'")
        
        if outcome_type not in ['YES', 'NO']:
            raise ValidationError(f"Invalid outcome_type: {outcome_type}. Must be 'YES' or 'NO'")
        
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValidationError("Amount must be greater than zero")
        
        # Get or create position
        position, created = Position.objects.get_or_create(
            user=user,
            market=market,
            defaults={
                'yes_tokens': Decimal('0'),
                'no_tokens': Decimal('0'),
                'total_staked': Decimal('0')
            }
        )
        
        # Get current token prices if not provided
        if execution_price is None:
            execution_price = PositionService._get_current_price(market, outcome_type)
        
        execution_price = Decimal(str(execution_price))
        
        # Update position based on side
        if side == 'BUY':
            PositionService._update_position_buy(position, outcome_type, amount, execution_price)
        else:  # SELL
            PositionService._update_position_sell(position, outcome_type, amount, execution_price)
        
        # Ensure no negative values
        position.yes_tokens = max(Decimal('0'), position.yes_tokens)
        position.no_tokens = max(Decimal('0'), position.no_tokens)
        position.total_staked = max(Decimal('0'), position.total_staked)
        
        # Save position
        position.save()
        
        return position
    
    @staticmethod
    def _update_position_buy(position, outcome_type, tokens_received, execution_price):
        """
        Update position for a BUY trade.
        
        Args:
            position: Position instance
            outcome_type: 'YES' or 'NO'
            tokens_received: Number of tokens received
            execution_price: Price at which tokens were bought
        """
        # Calculate amount staked (cost basis)
        amount_staked = tokens_received * execution_price
        
        # Update token count
        if outcome_type == 'YES':
            position.yes_tokens += tokens_received
        else:
            position.no_tokens += tokens_received
        
        # Update total staked
        position.total_staked += amount_staked
    
    @staticmethod
    def _update_position_sell(position, outcome_type, tokens_to_sell, execution_price):
        """
        Update position for a SELL trade.
        
        Args:
            position: Position instance
            outcome_type: 'YES' or 'NO'
            tokens_to_sell: Number of tokens to sell
            execution_price: Price at which tokens were sold
        
        Raises:
            ValidationError: If user doesn't have enough tokens
        """
        # Get current token balance
        current_tokens = position.yes_tokens if outcome_type == 'YES' else position.no_tokens
        
        # Validate sufficient tokens
        if current_tokens < tokens_to_sell:
            raise ValidationError(
                f"Insufficient {outcome_type} tokens. "
                f"Available: {current_tokens}, Required: {tokens_to_sell}"
            )
        
        # Calculate amount received
        amount_received = tokens_to_sell * execution_price
        
        # Calculate average entry price for the tokens being sold
        # Use proportional allocation since total_staked covers both YES and NO
        total_tokens = position.yes_tokens + position.no_tokens
        
        if position.total_staked > 0 and total_tokens > 0 and current_tokens > 0:
            # Calculate cost basis for this outcome type proportionally
            token_ratio = current_tokens / total_tokens
            allocated_staked = position.total_staked * token_ratio
            average_entry_price = allocated_staked / current_tokens
            cost_basis_sold = tokens_to_sell * average_entry_price
            
            # Update total staked proportionally
            position.total_staked -= cost_basis_sold
        else:
            # If no cost basis, reduce total_staked by amount received
            position.total_staked = max(Decimal('0'), position.total_staked - amount_received)
        
        # Update token count
        if outcome_type == 'YES':
            position.yes_tokens -= tokens_to_sell
        else:
            position.no_tokens -= tokens_to_sell
        
        # Ensure total_staked doesn't go negative
        position.total_staked = max(Decimal('0'), position.total_staked)
    
    @staticmethod
    def _get_current_price(market, outcome_type):
        """
        Get current price for an outcome token.
        
        Args:
            market: Market instance
            outcome_type: 'YES' or 'NO'
        
        Returns:
            Decimal: Current price of the outcome token
        """
        try:
            token = OutcomeToken.objects.get(market=market, outcome_type=outcome_type)
            return token.price
        except OutcomeToken.DoesNotExist:
            # Default to 0.5 if token doesn't exist
            return Decimal('0.5')
    
    @staticmethod
    def get_average_entry_price(position, outcome_type):
        """
        Calculate average entry price for a position's outcome tokens.
        
        Args:
            position: Position instance
            outcome_type: 'YES' or 'NO'
        
        Returns:
            Decimal: Average entry price, or 0 if no tokens held
        """
        tokens = position.yes_tokens if outcome_type == 'YES' else position.no_tokens
        
        if tokens <= 0:
            return Decimal('0')
        
        # If we have tokens, calculate average entry price
        # This is a simplified calculation - in reality, we'd need to track
        # separate cost basis for YES and NO tokens
        # For now, we'll use total_staked / total_tokens as approximation
        total_tokens = position.yes_tokens + position.no_tokens
        
        if total_tokens > 0 and position.total_staked > 0:
            # Proportionally allocate total_staked based on token ratio
            token_ratio = tokens / total_tokens
            allocated_staked = position.total_staked * token_ratio
            return allocated_staked / tokens
        
        return Decimal('0')
    
    @staticmethod
    def get_profit_loss_preview(position, market):
        """
        Calculate unrealized profit/loss preview for a position.
        
        Args:
            position: Position instance
            market: Market instance
        
        Returns:
            dict: Dictionary with profit/loss for YES and NO tokens
        """
        # Get current market prices
        try:
            yes_token = OutcomeToken.objects.get(market=market, outcome_type='YES')
            no_token = OutcomeToken.objects.get(market=market, outcome_type='NO')
            current_yes_price = yes_token.price
            current_no_price = no_token.price
        except OutcomeToken.DoesNotExist:
            current_yes_price = Decimal('0.5')
            current_no_price = Decimal('0.5')
        
        # Calculate average entry prices
        avg_entry_yes = PositionService.get_average_entry_price(position, 'YES')
        avg_entry_no = PositionService.get_average_entry_price(position, 'NO')
        
        # Calculate current value and profit/loss
        yes_current_value = position.yes_tokens * current_yes_price
        no_current_value = position.no_tokens * current_no_price
        
        yes_cost_basis = position.yes_tokens * avg_entry_yes if avg_entry_yes > 0 else Decimal('0')
        no_cost_basis = position.no_tokens * avg_entry_no if avg_entry_no > 0 else Decimal('0')
        
        yes_pnl = yes_current_value - yes_cost_basis
        no_pnl = no_current_value - no_cost_basis
        
        total_pnl = yes_pnl + no_pnl
        
        return {
            'yes': {
                'tokens': float(position.yes_tokens),
                'average_entry_price': float(avg_entry_yes),
                'current_price': float(current_yes_price),
                'current_value': float(yes_current_value),
                'cost_basis': float(yes_cost_basis),
                'profit_loss': float(yes_pnl),
                'profit_loss_percent': float((yes_pnl / yes_cost_basis * 100) if yes_cost_basis > 0 else 0)
            },
            'no': {
                'tokens': float(position.no_tokens),
                'average_entry_price': float(avg_entry_no),
                'current_price': float(current_no_price),
                'current_value': float(no_current_value),
                'cost_basis': float(no_cost_basis),
                'profit_loss': float(no_pnl),
                'profit_loss_percent': float((no_pnl / no_cost_basis * 100) if no_cost_basis > 0 else 0)
            },
            'total': {
                'current_value': float(yes_current_value + no_current_value),
                'total_cost_basis': float(yes_cost_basis + no_cost_basis),
                'total_profit_loss': float(total_pnl),
                'total_profit_loss_percent': float(
                    (total_pnl / (yes_cost_basis + no_cost_basis) * 100) 
                    if (yes_cost_basis + no_cost_basis) > 0 else 0
                )
            }
        }

