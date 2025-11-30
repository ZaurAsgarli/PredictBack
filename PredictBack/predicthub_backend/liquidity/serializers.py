from rest_framework import serializers
from .models import LiquidityEvent
from markets.serializers import MarketSerializer
from users.serializers import UserSerializer


class LiquidityEventSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    market = MarketSerializer(read_only=True)
    
    class Meta:
        model = LiquidityEvent
        fields = ['id', 'market', 'user', 'event_type', 'amount', 'created_at']
        read_only_fields = ['created_at']

