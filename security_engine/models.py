"""
Security logging models for tracking security events
"""
from django.db import models
from django.utils import timezone


class SecurityLog(models.Model):
    """
    Database table for storing security events such as rate limit violations
    and failed login attempts.
    """
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    EVENT_TYPE_CHOICES = [
        ('RATE_LIMIT', 'Rate Limit Exceeded'),
        ('FAILED_LOGIN', 'Failed Login Attempt'),
        ('UNAUTHORIZED_ACCESS', 'Unauthorized Access'),
        ('SUSPICIOUS_ACTIVITY', 'Suspicious Activity'),
    ]
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES, db_index=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='MEDIUM')
    message = models.TextField(blank=True, null=True)
    path = models.CharField(max_length=255, blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True, help_text="User agent string from request")
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional metadata in JSON format")
    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_logs'
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['event_type', '-timestamp']),
            models.Index(fields=['ip', '-timestamp']),
        ]
        db_table = 'security_logs'
    
    def __str__(self):
        return f"{self.event_type} from {self.ip} at {self.timestamp}"


class LoginAttempt(models.Model):
    """
    Detailed tracking of login attempts with comprehensive information
    for security analysis and threat detection.
    """
    STATUS_CHOICES = [
        ('SUCCESS', 'Successful'),
        ('FAILED', 'Failed'),
        ('BLOCKED', 'Blocked'),
    ]
    
    FAILURE_REASON_CHOICES = [
        ('INVALID_CREDENTIALS', 'Invalid email or password'),
        ('ACCOUNT_DISABLED', 'Account is disabled'),
        ('ACCOUNT_LOCKED', 'Account is locked'),
        ('TOO_MANY_ATTEMPTS', 'Too many failed attempts'),
        ('SUSPICIOUS_IP', 'Suspicious IP address'),
        ('MISSING_CREDENTIALS', 'Missing email or password'),
    ]
    
    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Authentication details
    email = models.EmailField(db_index=True, help_text="Email address used in login attempt")
    success = models.BooleanField(default=False, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='FAILED', db_index=True)
    failure_reason = models.CharField(
        max_length=50,
        choices=FAILURE_REASON_CHOICES,
        null=True,
        blank=True,
        help_text="Reason for failure if login was unsuccessful"
    )
    
    # User information
    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='login_attempts',
        help_text="User if login was successful"
    )
    
    # Request details
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    user_agent = models.TextField(blank=True, null=True, help_text="User agent string from request")
    request_path = models.CharField(max_length=255, blank=True, null=True)
    
    # Additional metadata
    country = models.CharField(max_length=2, blank=True, null=True, help_text="Country code from IP")
    city = models.CharField(max_length=100, blank=True, null=True)
    device_type = models.CharField(max_length=50, blank=True, null=True, help_text="Mobile, Desktop, Tablet, etc.")
    browser = models.CharField(max_length=100, blank=True, null=True)
    os = models.CharField(max_length=100, blank=True, null=True, help_text="Operating system")
    
    # Security flags
    is_suspicious = models.BooleanField(default=False, db_index=True)
    is_bot = models.BooleanField(default=False, db_index=True)
    risk_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text="Risk score from 0-100"
    )
    
    # Additional data (JSON field for flexible storage)
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional metadata in JSON format")
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['email', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
            models.Index(fields=['success', '-timestamp']),
            models.Index(fields=['status', '-timestamp']),
            models.Index(fields=['is_suspicious', '-timestamp']),
        ]
        db_table = 'login_attempts'
        verbose_name = 'Login Attempt'
        verbose_name_plural = 'Login Attempts'
    
    def __str__(self):
        status_str = "✓" if self.success else "✗"
        return f"{status_str} {self.email} from {self.ip_address} at {self.timestamp}"
    
    @property
    def is_recent_failure(self):
        """Check if this is a recent failed attempt (within last hour)"""
        if self.success:
            return False
        time_diff = timezone.now() - self.timestamp
        return time_diff.total_seconds() < 3600
    
    @classmethod
    def get_recent_failures(cls, email=None, ip_address=None, hours=1):
        """Get recent failed login attempts"""
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(hours=hours)
        queryset = cls.objects.filter(
            success=False,
            timestamp__gte=cutoff
        )
        if email:
            queryset = queryset.filter(email=email)
        if ip_address:
            queryset = queryset.filter(ip_address=ip_address)
        return queryset
    
    @classmethod
    def count_recent_failures(cls, email=None, ip_address=None, hours=1):
        """Count recent failed login attempts"""
        return cls.get_recent_failures(email, ip_address, hours).count()

