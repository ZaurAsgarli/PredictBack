"""
Django models for storing ML model predictions and results.

This module provides database storage for:
- Trade risk predictions (Model 1)
- Market manipulation scores (Model 4)
- Platform health metrics (Model 5)
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from backend_api.api.users.models import User
from backend_api.api.markets.models import Market
from backend_api.api.trades.models import Trade


class TradeRiskPrediction(models.Model):
    """
    Stores Model 1 (Suspicious Trades) predictions.
    """
    RISK_LEVEL_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    trade = models.ForeignKey(
        Trade,
        on_delete=models.CASCADE,
        related_name='risk_predictions',
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='risk_predictions',
        null=True,
        blank=True,
    )
    market = models.ForeignKey(
        Market,
        on_delete=models.CASCADE,
        related_name='risk_predictions',
        null=True,
        blank=True,
    )
    
    # Model outputs
    score = models.FloatField(
        help_text="Anomaly score from Isolation Forest model",
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)]
    )
    label = models.IntegerField(
        help_text="Prediction label: 1 (normal) or -1 (anomaly)"
    )
    risk_level = models.CharField(
        max_length=20,
        choices=RISK_LEVEL_CHOICES,
        default='LOW'
    )
    
    # Input features (for audit/debugging)
    amount_staked = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    time_since_last_trade = models.FloatField(null=True, blank=True)
    hour_of_day = models.IntegerField(null=True, blank=True)
    user_total_trades = models.IntegerField(null=True, blank=True)
    user_avg_stake = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Metadata
    model_version = models.CharField(max_length=50, default='v1.0')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['trade']),
            models.Index(fields=['risk_level', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Risk Prediction: {self.risk_level} (score: {self.score:.3f})"


class MarketManipulationScore(models.Model):
    """
    Stores Model 4 (Market Manipulation) scores.
    """
    RISK_LEVEL_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    market = models.ForeignKey(
        Market,
        on_delete=models.CASCADE,
        related_name='manipulation_scores'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='manipulation_scores',
        null=True,
        blank=True,
    )
    
    # Model outputs
    manipulation_score = models.FloatField(
        help_text="Overall manipulation score (0-1)",
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    is_manipulation_suspected = models.BooleanField(default=False)
    risk_level = models.CharField(
        max_length=20,
        choices=RISK_LEVEL_CHOICES,
        default='LOW'
    )
    
    # Component scores
    pump_dump_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    wash_trading_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    clique_id = models.IntegerField(null=True, blank=True)
    
    # Metadata
    time_window_minutes = models.IntegerField(default=60)
    model_version = models.CharField(max_length=50, default='v1.0')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = [['market', 'user', 'created_at']]  # One score per market/user/time
        indexes = [
            models.Index(fields=['market', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['is_manipulation_suspected', '-created_at']),
            models.Index(fields=['risk_level', '-created_at']),
        ]
    
    def __str__(self):
        return f"Manipulation Score: {self.market.title} - {self.risk_level}"


class PlatformHealthMetric(models.Model):
    """
    Stores Model 5 (MHEWS) platform health metrics.
    """
    HEALTH_STATUS_CHOICES = [
        ('HEALTHY', 'Healthy'),
        ('STABLE', 'Stable'),
        ('ELEVATED', 'Elevated'),
        ('WARNING', 'Warning'),
        ('CRITICAL', 'Critical'),
    ]
    
    ALERT_LEVEL_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    # Composite metrics
    platform_stress_level = models.FloatField(
        help_text="Platform stress level (0-1)",
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    systemic_risk_index = models.FloatField(
        help_text="Systemic risk index (0-1)",
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    health_status = models.CharField(
        max_length=20,
        choices=HEALTH_STATUS_CHOICES,
        default='HEALTHY'
    )
    alert_level = models.CharField(
        max_length=20,
        choices=ALERT_LEVEL_CHOICES,
        default='LOW'
    )
    
    # Model contributions
    model1_stress_score = models.FloatField(default=0.0)
    model2_stress_score = models.FloatField(default=0.0)
    model3_stress_score = models.FloatField(default=0.0)
    model4_stress_score = models.FloatField(default=0.0)
    
    # Detailed metrics
    model1_anomaly_rate = models.FloatField(null=True, blank=True)
    model2_avg_hhi = models.FloatField(null=True, blank=True)
    model3_avg_volatility = models.FloatField(null=True, blank=True)
    model4_manipulation_rate = models.FloatField(null=True, blank=True)
    
    # Alert messages
    alert_messages = models.TextField(blank=True)
    
    # Metadata
    aggregation_window_hours = models.IntegerField(default=24)
    model_version = models.CharField(max_length=50, default='v1.0')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['health_status', '-created_at']),
            models.Index(fields=['alert_level', '-created_at']),
        ]
    
    def __str__(self):
        return f"Health Metric: {self.health_status} ({self.created_at})"


class ModelPredictionAudit(models.Model):
    """
    Audit log for all model predictions (for compliance and debugging).
    """
    MODEL_CHOICES = [
        ('model1', 'Model 1: Suspicious Trades'),
        ('model2', 'Model 2: Position Exposure'),
        ('model3', 'Model 3: Token Forecasting'),
        ('model4', 'Model 4: Market Manipulation'),
        ('model5', 'Model 5: Platform Health'),
    ]
    
    model_name = models.CharField(max_length=20, choices=MODEL_CHOICES)
    input_data = models.JSONField(help_text="Input data to the model")
    output_data = models.JSONField(help_text="Model output/prediction")
    execution_time_ms = models.FloatField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['model_name', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.model_name} prediction at {self.created_at}"

