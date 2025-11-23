from django.db import models
from django.conf import settings
from markets.models import Market  # adjust import if your app name is different

class OnchainTransaction(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    ]

    tx_hash = models.CharField(max_length=80, unique=True)
    network = models.CharField(max_length=32, default="sepolia")
    block_number = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="PENDING")
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["tx_hash"]),  # Hot-path: tx_hash
            models.Index(fields=["network", "status"]),
            models.Index(fields=["block_number"]),  # Hot-path: block_number
        ]

    def __str__(self):
        return f"{self.network}:{self.tx_hash[:10]}... ({self.status})"


class OnchainEventLog(models.Model):
    onchain_tx = models.ForeignKey(
        "indexer.OnchainTransaction",
        related_name="events",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    event_name = models.CharField(max_length=64)
    tx_hash = models.CharField(max_length=80)
    log_index = models.IntegerField()
    market = models.ForeignKey(
        Market, null=True, blank=True, on_delete=models.SET_NULL, related_name="onchain_events"
    )
    user_address = models.CharField(max_length=64, blank=True)
    payload_json = models.JSONField()
    processed_at = models.DateTimeField(null=True, blank=True)
    duplicate = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("tx_hash", "log_index")
        indexes = [
            models.Index(fields=["tx_hash"]),  # Hot-path: tx_hash
            models.Index(fields=["market"]),  # Hot-path: market_id
            models.Index(fields=["event_name"]),  # Hot-path: event_name
            models.Index(fields=["user_address"]),
        ]

    def __str__(self):
        return f"{self.event_name} #{self.log_index} ({self.tx_hash[:10]}...)"
