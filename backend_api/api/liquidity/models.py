from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from backend_api.api.users.models import User
from backend_api.api.markets.models import Market


class LiquidityEvent(models.Model):
    """Tracks AMM liquidity changes"""
    EVENT_TYPE_CHOICES = [
        ('add', 'Add'),
        ('remove', 'Remove'),
    ]
    
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='liquidity_events')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='liquidity_events')
    event_type = models.CharField(max_length=10, choices=EVENT_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    onchain_tx_hash = models.CharField(max_length=80, blank=True, null=True, db_index=True)
    onchain_liquidity_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['market']),  # Hot-path: market_id
            models.Index(fields=['market', '-created_at']),
            models.Index(fields=['user']),  # Hot-path: user_id
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['event_type', '-created_at']),
            models.Index(fields=['onchain_tx_hash']),  # Hot-path: tx_hash
            models.Index(fields=['market', 'event_type']),
        ]
    
    def __str__(self):
        return f"{self.event_type} {self.amount} by {self.user.username} for {self.market.title}"

