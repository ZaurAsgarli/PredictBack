from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom User model with prediction market specific fields"""
    
    ROLE_CHOICES = [
        ('user', 'User'),
        ('admin', 'Admin'),
    ]
    
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    total_points = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    win_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    streak = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
        ordering = ['-total_points']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['-total_points']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return self.username

