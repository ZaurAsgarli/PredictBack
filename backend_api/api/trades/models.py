from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from backend_api.api.users.models import User
from backend_api.api.markets.models import Market


class Trade(models.Model):
    """Represents a buy/sell trade of outcome tokens"""
    TRADE_TYPE_CHOICES = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
    ]
    
    OUTCOME_CHOICES = [
        ('YES', 'YES'),
        ('NO', 'NO'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trades')
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='trades')
    outcome_type = models.CharField(max_length=10, choices=OUTCOME_CHOICES)
    trade_type = models.CharField(max_length=10, choices=TRADE_TYPE_CHOICES)
    amount_staked = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    tokens_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    price_at_execution = models.DecimalField(max_digits=8, decimal_places=6)
    onchain_tx_hash = models.CharField(max_length=80, blank=True, null=True, db_index=True)
    onchain_trade_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),  # Hot-path: user_id
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['market']),  # Hot-path: market_id
            models.Index(fields=['market', '-created_at']),
            models.Index(fields=['outcome_type']),  # Hot-path: outcome_type
            models.Index(fields=['outcome_type', '-created_at']),
            models.Index(fields=['trade_type', '-created_at']),
            models.Index(fields=['onchain_tx_hash']),  # Hot-path: tx_hash
            models.Index(fields=['market', 'outcome_type']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.trade_type} {self.outcome_type} - {self.market.title}"

