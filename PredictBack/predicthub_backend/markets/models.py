from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from users.models import User


class MarketCategory(models.Model):
    """Categories for markets"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Market Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Market(models.Model):
    """Represents a prediction market event"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('resolved', 'Resolved'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(MarketCategory, on_delete=models.PROTECT, related_name='markets')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    resolution_outcome = models.CharField(max_length=10, null=True, blank=True, choices=[('YES', 'YES'), ('NO', 'NO')])
    liquidity_pool = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, validators=[MinValueValidator(Decimal('0'))])
    fee_percentage = models.DecimalField(max_digits=5, decimal_places=4, default=0.02)
    onchain_market_id = models.BigIntegerField(null=True, blank=True, unique=True, db_index=True)
    onchain_tx_hash = models.CharField(max_length=80, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ends_at = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_markets')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['ends_at']),
            models.Index(fields=['created_by']),
            models.Index(fields=['onchain_market_id']),
            models.Index(fields=['onchain_tx_hash']),
        ]
    
    def __str__(self):
        return self.title
    
    def calculate_prices(self):
        """Calculate YES/NO prices using AMM logic"""
        yes_token = OutcomeToken.objects.filter(market=self, outcome_type='YES').first()
        no_token = OutcomeToken.objects.filter(market=self, outcome_type='NO').first()
        
        if not yes_token or not no_token:
            return {'yes_price': 0.5, 'no_price': 0.5}
        
        total_liquidity = yes_token.supply + no_token.supply
        if total_liquidity == 0:
            return {'yes_price': 0.5, 'no_price': 0.5}
        
        yes_price = float(yes_token.supply) / float(total_liquidity)
        no_price = float(no_token.supply) / float(total_liquidity)
        
        return {'yes_price': yes_price, 'no_price': no_price}


class OutcomeToken(models.Model):
    """Represents YES/NO outcome tokens for a market"""
    OUTCOME_CHOICES = [
        ('YES', 'YES'),
        ('NO', 'NO'),
    ]
    
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='outcome_tokens')
    outcome_type = models.CharField(max_length=10, choices=OUTCOME_CHOICES)
    price = models.DecimalField(max_digits=8, decimal_places=6, default=0.5)
    supply = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, validators=[MinValueValidator(Decimal('0'))])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['market', 'outcome_type']
        indexes = [
            models.Index(fields=['market', 'outcome_type']),
            models.Index(fields=['market', '-updated_at']),
        ]
    
    def __str__(self):
        return f"{self.market.title} - {self.outcome_type}"


class PriceHistory(models.Model):
    """Historical price data for charts"""
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='price_history')
    yes_price = models.DecimalField(max_digits=8, decimal_places=6)
    no_price = models.DecimalField(max_digits=8, decimal_places=6)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['market', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.market.title} - {self.timestamp}"


class Resolution(models.Model):
    """Final resolution of a market"""
    market = models.OneToOneField(Market, on_delete=models.CASCADE, related_name='resolution')
    resolved_outcome = models.CharField(max_length=10, choices=[('YES', 'YES'), ('NO', 'NO')])
    resolver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='resolved_markets')
    dispute_window = models.DateTimeField()
    bond_amount = models.DecimalField(max_digits=10, decimal_places=2, default=100.0)
    onchain_tx_hash = models.CharField(max_length=80, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['market']),
            models.Index(fields=['resolved_outcome']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['onchain_tx_hash']),
        ]
    
    def __str__(self):
        return f"{self.market.title} - {self.resolved_outcome}"

