from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from users.models import User
from markets.models import Market


class Position(models.Model):
    """Tracks user's accumulated holdings in a market"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='positions')
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='positions')
    yes_tokens = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, validators=[MinValueValidator(Decimal('0'))])
    no_tokens = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, validators=[MinValueValidator(Decimal('0'))])
    total_staked = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, validators=[MinValueValidator(Decimal('0'))])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'market']
        indexes = [
            models.Index(fields=['user']),  # Hot-path: user_id
            models.Index(fields=['user', '-updated_at']),
            models.Index(fields=['market']),  # Hot-path: market_id
            models.Index(fields=['market', '-updated_at']),
            models.Index(fields=['user', 'market']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.market.title}"

