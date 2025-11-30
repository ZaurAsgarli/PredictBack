"""
Market service for managing market status and lifecycle
"""
from django.utils import timezone
from django.db import transaction
from decimal import Decimal

from markets.models import Market


class MarketService:
    """Service for managing market operations"""
    
    @staticmethod
    @transaction.atomic
    def update_status(market):
        """
        Update market status based on current state.
        
        Status priority:
        1. If resolved event arrived (has resolution) → status="resolved"
        2. If liquidity dry (liquidity_pool == 0) or expired (ends_at < now) → status="closed"
        3. Otherwise → status="active"
        
        Args:
            market: Market instance to update
        
        Returns:
            Market: Updated market instance
        """
        # Check if market has been resolved
        has_resolution = hasattr(market, 'resolution') and market.resolution is not None
        
        if has_resolution:
            # Market has been resolved
            if market.status != 'resolved':
                market.status = 'resolved'
                market.resolution_outcome = market.resolution.resolved_outcome
                market.save(update_fields=['status', 'resolution_outcome'])
            return market
        
        # Check if market is expired
        is_expired = market.ends_at < timezone.now()
        
        # Check if liquidity is dry (liquidity_pool is 0 or very low)
        liquidity_dry = market.liquidity_pool <= Decimal('0')
        
        if is_expired or liquidity_dry:
            # Market should be closed
            if market.status != 'closed':
                market.status = 'closed'
                market.save(update_fields=['status'])
            return market
        
        # Market is active
        if market.status != 'active':
            market.status = 'active'
            market.save(update_fields=['status'])
        
        return market

