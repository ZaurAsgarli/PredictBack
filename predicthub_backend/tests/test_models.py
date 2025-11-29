"""
Tests for models
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from markets.models import Market, MarketCategory, OutcomeToken
from trades.models import Trade
from positions.models import Position

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    def test_create_user(self):
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.total_points == 0
        assert user.win_rate == 0
        assert user.streak == 0


@pytest.mark.django_db
class TestMarketModel:
    def test_create_market(self):
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
            ends_at=timezone.now() + timedelta(days=30),
            liquidity_pool=Decimal('1000.00')
        )
        assert market.title == 'Test Market'
        assert market.status == 'active'
        assert market.liquidity_pool == Decimal('1000.00')
    
    def test_calculate_prices(self):
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
        
        OutcomeToken.objects.create(
            market=market,
            outcome_type='YES',
            supply=Decimal('600.00'),
            price=Decimal('0.6')
        )
        OutcomeToken.objects.create(
            market=market,
            outcome_type='NO',
            supply=Decimal('400.00'),
            price=Decimal('0.4')
        )
        
        prices = market.calculate_prices()
        assert prices['yes_price'] == 0.6
        assert prices['no_price'] == 0.4


@pytest.mark.django_db
class TestTradeModel:
    def test_create_trade(self):
        category = MarketCategory.objects.create(
            name='Sports',
            slug='sports'
        )
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        market = Market.objects.create(
            title='Test Market',
            description='Test Description',
            category=category,
            created_by=user,
            ends_at=timezone.now() + timedelta(days=30)
        )
        
        trade = Trade.objects.create(
            user=user,
            market=market,
            outcome_type='YES',
            trade_type='buy',
            amount_staked=Decimal('100.00'),
            tokens_amount=Decimal('200.00'),
            price_at_execution=Decimal('0.5')
        )
        
        assert trade.user == user
        assert trade.market == market
        assert trade.outcome_type == 'YES'
        assert trade.trade_type == 'buy'

