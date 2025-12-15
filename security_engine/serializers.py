from rest_framework import serializers
from .models import SecurityLog, LoginAttempt


class SecurityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityLog
        fields = ['id', 'timestamp', 'ip', 'event_type', 'severity', 'message', 'path', 'user']
        read_only_fields = ['id', 'timestamp']


class LoginAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginAttempt
        fields = [
            'id', 'timestamp', 'email', 'success', 'status', 'failure_reason',
            'user', 'ip_address', 'user_agent', 'request_path',
            'country', 'city', 'device_type', 'browser', 'os',
            'is_suspicious', 'is_bot', 'risk_score', 'metadata'
        ]
        read_only_fields = ['id', 'timestamp']

