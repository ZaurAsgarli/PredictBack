"""
Tests for API endpoints
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from markets.models import Market, MarketCategory

User = get_user_model()


@pytest.mark.django_db
class TestAuthAPI:
    def test_signup(self):
        client = APIClient()
        response = client.post('/auth/signup/', {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123'
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert 'tokens' in response.data
        assert 'user' in response.data
    
    def test_login(self):
        User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        client = APIClient()
        response = client.post('/auth/login/', {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        assert response.status_code == status.HTTP_200_OK
        assert 'tokens' in response.data
    
    def test_me_endpoint(self):
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/auth/me/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['username'] == 'testuser'


@pytest.mark.django_db
class TestMarketsAPI:
    def test_list_markets(self):
        category = MarketCategory.objects.create(
            name='Sports',
            slug='sports'
        )
        user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        Market.objects.create(
            title='Test Market',
            description='Test Description',
            category=category,
            created_by=user,
            ends_at=timezone.now() + timedelta(days=30)
        )
        
        client = APIClient()
        response = client.get('/markets/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) > 0
    
    def test_get_market_detail(self):
        category = MarketCategory.objects.create(
            name='Sports',
            slug='sports'
        )
        user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        market = Market.objects.create(
            title='Test Market',
            description='Test Description',
            category=category,
            created_by=user,
            ends_at=timezone.now() + timedelta(days=30)
        )
        
        client = APIClient()
        response = client.get(f'/markets/{market.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Test Market'

