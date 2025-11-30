from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from users.models import User
from markets.models import Market


class Dispute(models.Model):
    """Represents a dispute against a market resolution"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='disputes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='disputes')
    bond_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['market']),  # Hot-path: market_id
            models.Index(fields=['market', 'status']),
            models.Index(fields=['user']),  # Hot-path: user_id
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"Dispute by {self.user.username} for {self.market.title}"

