from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from .models import SecurityLog, LoginAttempt
from .serializers import SecurityLogSerializer, LoginAttemptSerializer


class SecurityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing security logs.
    Only accessible to authenticated admin users.
    """
    queryset = SecurityLog.objects.all()
    serializer_class = SecurityLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = SecurityLog.objects.all()
        
        # Filter by event type if provided
        event_type = self.request.query_params.get('event_type', None)
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        
        # Filter by severity if provided
        severity = self.request.query_params.get('severity', None)
        if severity:
            queryset = queryset.filter(severity=severity)
        
        # Filter by IP if provided
        ip = self.request.query_params.get('ip', None)
        if ip:
            queryset = queryset.filter(ip=ip)
        
        # Filter by time range (last N hours)
        hours = self.request.query_params.get('hours', None)
        if hours:
            try:
                hours = int(hours)
                since = timezone.now() - timedelta(hours=hours)
                queryset = queryset.filter(timestamp__gte=since)
            except ValueError:
                pass
        
        return queryset.order_by('-timestamp')
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get statistics about security logs"""
        queryset = self.get_queryset()
        
        total = queryset.count()
        by_type = {}
        by_severity = {}
        
        for log in queryset:
            by_type[log.event_type] = by_type.get(log.event_type, 0) + 1
            by_severity[log.severity] = by_severity.get(log.severity, 0) + 1
        
        return Response({
            'total': total,
            'by_event_type': by_type,
            'by_severity': by_severity,
        })


# Simple API view for dashboard (no authentication required for demo)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


@api_view(['GET'])
@permission_classes([AllowAny])  # For demo purposes - should be IsAuthenticated in production
def security_logs_list(request):
    """
    Simple endpoint for dashboard to fetch security logs.
    Returns JSON array of security logs.
    """
    queryset = SecurityLog.objects.all().order_by('-timestamp')[:100]  # Limit to 100 most recent
    serializer = SecurityLogSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def test_endpoint(request):
    """
    Simple test endpoint for rate limiting tests.
    Returns a simple JSON response.
    """
    from django.utils import timezone
    return Response({
        'message': 'Test endpoint working',
        'timestamp': timezone.now().isoformat()
    })


class LoginAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing login attempts.
    Only accessible to authenticated admin users.
    """
    queryset = LoginAttempt.objects.all()
    serializer_class = LoginAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = LoginAttempt.objects.all()
        
        # Filter by email if provided
        email = self.request.query_params.get('email', None)
        if email:
            queryset = queryset.filter(email=email)
        
        # Filter by IP if provided
        ip_address = self.request.query_params.get('ip', None)
        if ip_address:
            queryset = queryset.filter(ip_address=ip_address)
        
        # Filter by success status
        success = self.request.query_params.get('success', None)
        if success is not None:
            success_bool = success.lower() == 'true'
            queryset = queryset.filter(success=success_bool)
        
        # Filter by suspicious flag
        is_suspicious = self.request.query_params.get('is_suspicious', None)
        if is_suspicious is not None:
            suspicious_bool = is_suspicious.lower() == 'true'
            queryset = queryset.filter(is_suspicious=suspicious_bool)
        
        # Filter by time range (last N hours)
        hours = self.request.query_params.get('hours', None)
        if hours:
            try:
                hours = int(hours)
                since = timezone.now() - timedelta(hours=hours)
                queryset = queryset.filter(timestamp__gte=since)
            except ValueError:
                pass
        
        return queryset.order_by('-timestamp')
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get statistics about login attempts"""
        queryset = self.get_queryset()
        
        total = queryset.count()
        successful = queryset.filter(success=True).count()
        failed = queryset.filter(success=False).count()
        suspicious = queryset.filter(is_suspicious=True).count()
        
        by_status = {}
        for attempt in queryset:
            status = attempt.status
            by_status[status] = by_status.get(status, 0) + 1
        
        return Response({
            'total': total,
            'successful': successful,
            'failed': failed,
            'suspicious': suspicious,
            'by_status': by_status,
        })

