"""
Seed script for PredictHub backend
Run with: python manage.py shell < seed.py
Or: python manage.py runscript seed (if using django-extensions)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from users.models import User
from markets.models import Market, MarketCategory, OutcomeToken, PriceHistory
from trades.models import Trade
from positions.models import Position


def seed_data():
    print("Starting seed process...")
    
    # Create categories
    categories_data = [
        {'name': 'Sports', 'slug': 'sports', 'description': 'Sports predictions'},
        {'name': 'Politics', 'slug': 'politics', 'description': 'Political predictions'},
        {'name': 'Technology', 'slug': 'technology', 'description': 'Tech predictions'},
        {'name': 'Entertainment', 'slug': 'entertainment', 'description': 'Entertainment predictions'},
        {'name': 'Finance', 'slug': 'finance', 'description': 'Financial predictions'},
    ]
    
    categories = {}
    for cat_data in categories_data:
        category, created = MarketCategory.objects.get_or_create(
            slug=cat_data['slug'],
            defaults=cat_data
        )
        categories[cat_data['slug']] = category
        print(f"{'Created' if created else 'Found'} category: {category.name}")
    
    # Create sample users
    users = []
    for i in range(5):
        user, created = User.objects.get_or_create(
            email=f'user{i+1}@example.com',
            defaults={
                'username': f'user{i+1}',
                'total_points': Decimal(str((i+1) * 100)),
                'win_rate': Decimal(str(50 + i * 10)),
                'streak': i,
            }
        )
        if created:
            user.set_password('password123')
            user.save()
        users.append(user)
        print(f"{'Created' if created else 'Found'} user: {user.username}")
    
    # Create sample markets
    markets_data = [
        {
            'title': 'Will Team A win the championship?',
            'description': 'Prediction on whether Team A will win the championship this season.',
            'category': categories['sports'],
            'ends_at': timezone.now() + timedelta(days=30),
        },
        {
            'title': 'Will the new policy be implemented?',
            'description': 'Prediction on whether the new policy will be implemented this year.',
            'category': categories['politics'],
            'ends_at': timezone.now() + timedelta(days=60),
        },
        {
            'title': 'Will the new product launch this quarter?',
            'description': 'Prediction on whether the new tech product will launch in Q1.',
            'category': categories['technology'],
            'ends_at': timezone.now() + timedelta(days=90),
        },
        {
            'title': 'Will the movie gross over $100M?',
            'description': 'Prediction on whether the upcoming movie will gross over $100M.',
            'category': categories['entertainment'],
            'ends_at': timezone.now() + timedelta(days=45),
        },
        {
            'title': 'Will the stock price reach $200?',
            'description': 'Prediction on whether the stock price will reach $200 by end of year.',
            'category': categories['finance'],
            'ends_at': timezone.now() + timedelta(days=120),
        },
    ]
    
    markets = []
    for market_data in markets_data:
        market = Market.objects.create(
            **market_data,
            created_by=users[0],
            liquidity_pool=Decimal('1000.00'),
            fee_percentage=Decimal('0.02'),
        )
        
        # Create outcome tokens
        OutcomeToken.objects.create(
            market=market,
            outcome_type='YES',
            supply=Decimal('500.00'),
            price=Decimal('0.5')
        )
        OutcomeToken.objects.create(
            market=market,
            outcome_type='NO',
            supply=Decimal('500.00'),
            price=Decimal('0.5')
        )
        
        # Create initial price history
        PriceHistory.objects.create(
            market=market,
            yes_price=Decimal('0.5'),
            no_price=Decimal('0.5')
        )
        
        markets.append(market)
        print(f"Created market: {market.title}")
    
    # Create sample trades
    for i, market in enumerate(markets[:3]):  # Only for first 3 markets
        for j, user in enumerate(users[:3]):  # Only for first 3 users
            trade = Trade.objects.create(
                user=user,
                market=market,
                outcome_type='YES' if j % 2 == 0 else 'NO',
                trade_type='buy',
                amount_staked=Decimal(str((j+1) * 10)),
                tokens_amount=Decimal(str((j+1) * 20)),
                price_at_execution=Decimal('0.5')
            )
            
            # Create or update position
            position, created = Position.objects.get_or_create(
                user=user,
                market=market,
                defaults={
                    'yes_tokens': Decimal('0'),
                    'no_tokens': Decimal('0'),
                    'total_staked': Decimal('0')
                }
            )
            
            if trade.outcome_type == 'YES':
                position.yes_tokens += trade.tokens_amount
            else:
                position.no_tokens += trade.tokens_amount
            position.total_staked += trade.amount_staked
            position.save()
            
            print(f"Created trade: {user.username} - {market.title}")
    
    print("\nSeed process completed successfully!")
    print(f"Created {len(categories)} categories")
    print(f"Created {len(users)} users")
    print(f"Created {len(markets)} markets")
    print(f"Created {Trade.objects.count()} trades")
    print(f"Created {Position.objects.count()} positions")


if __name__ == '__main__':
    seed_data()

