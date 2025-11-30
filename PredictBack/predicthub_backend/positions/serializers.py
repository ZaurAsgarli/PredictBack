from rest_framework import serializers
from .models import Position
from markets.serializers import MarketSerializer
from users.serializers import UserSerializer


class PositionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    market = MarketSerializer(read_only=True)
    
    class Meta:
        model = Position
        fields = [
            'id', 'user', 'market', 'yes_tokens', 'no_tokens',
            'total_staked', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

