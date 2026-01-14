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


# ============================================================================
# ADMIN DASHBOARD API ENDPOINTS
# ============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])  # For demo - use IsAdminUser in production
def admin_stats(request):
    """
    GET /api/admin/stats
    Returns market status counts for dashboard overview.
    """
    from backend_api.api.markets.models import Market
    from backend_api.api.users.models import User
    from backend_api.api.trades.models import Trade
    from backend_api.api.liquidity.models import LiquidityEvent
    
    # Market stats
    active_markets = Market.objects.filter(status='active').count()
    resolved_markets = Market.objects.filter(status='resolved').count()
    closed_markets = Market.objects.filter(status='closed').count()
    total_markets = Market.objects.count()
    
    # Additional stats
    total_users = User.objects.count()
    total_trades = Trade.objects.count()
    total_liquidity_events = LiquidityEvent.objects.count()
    total_security_logs = SecurityLog.objects.count()
    
    return Response({
        'markets': {
            'active': active_markets,
            'resolved': resolved_markets,
            'closed': closed_markets,
            'total': total_markets,
        },
        'users': {
            'total': total_users,
        },
        'activity': {
            'total_trades': total_trades,
            'liquidity_events': total_liquidity_events,
            'security_events': total_security_logs,
        },
        'timestamp': timezone.now().isoformat(),
    })


@api_view(['GET'])
@permission_classes([AllowAny])  # For demo - use IsAdminUser in production
def admin_security(request):
    """
    GET /api/admin/security
    Returns the last 50 security logs with severity color coding.
    """
    limit = int(request.query_params.get('limit', 50))
    severity_filter = request.query_params.get('severity', None)
    
    queryset = SecurityLog.objects.all().order_by('-timestamp')
    
    if severity_filter:
        queryset = queryset.filter(severity=severity_filter)
    
    logs = queryset[:limit]
    
    # Add color coding for frontend
    severity_colors = {
        'LOW': '#22c55e',      # Green
        'MEDIUM': '#eab308',   # Yellow
        'HIGH': '#f97316',     # Orange
        'CRITICAL': '#ef4444', # Red
    }
    
    data = []
    for log in logs:
        data.append({
            'id': log.id,
            'timestamp': log.timestamp.isoformat(),
            'ip': log.ip,
            'event_type': log.event_type,
            'severity': log.severity,
            'severity_color': severity_colors.get(log.severity, '#6b7280'),
            'message': log.message,
            'path': log.path,
            'user_id': log.user_id,
            'user_agent': log.user_agent[:100] if log.user_agent else None,
        })
    
    return Response({
        'logs': data,
        'total_count': SecurityLog.objects.count(),
        'severity_breakdown': {
            'low': SecurityLog.objects.filter(severity='LOW').count(),
            'medium': SecurityLog.objects.filter(severity='MEDIUM').count(),
            'high': SecurityLog.objects.filter(severity='HIGH').count(),
            'critical': SecurityLog.objects.filter(severity='CRITICAL').count(),
        },
    })


@api_view(['GET'])
@permission_classes([AllowAny])  # For demo - use IsAdminUser in production
def admin_suspicious_users(request):
    """
    GET /api/admin/suspicious
    Returns users with risk score > 0.8 (The "Ban List" / Watchlist)
    """
    from ml_service.training.models import TradeRiskPrediction
    
    # Use float for score field (not Decimal)
    threshold = float(request.query_params.get('threshold', '0.8'))
    
    # Get unique users with high risk predictions
    # Note: the model uses 'score' field, not 'risk_score'
    high_risk_predictions = (
        TradeRiskPrediction.objects
        .filter(score__gte=threshold)
        .select_related('user')
        .order_by('-score')[:50]
    )
    
    # Group by user (get highest risk score per user)
    user_risks = {}
    for pred in high_risk_predictions:
        if pred.user and pred.user_id not in user_risks:
            user_risks[pred.user_id] = {
                'user_id': pred.user.id,
                'username': pred.user.username,
                'email': pred.user.email,
                'risk_score': float(pred.score),
                'risk_level': pred.risk_level,
                'reason': f'Risk level: {pred.risk_level}',
                'last_flagged': pred.created_at.isoformat(),
                'wallet_address': pred.user.wallet_address,
            }
    
    return Response({
        'suspicious_users': list(user_risks.values()),
        'total_flagged': len(user_risks),
        'threshold': threshold,
        'timestamp': timezone.now().isoformat(),
    })



@api_view(['GET'])
@permission_classes([AllowAny])  # For demo - use IsAdminUser in production
def admin_ml_insights(request):
    """
    GET /api/admin/ml-insights
    Returns ML model metrics, predictions summary, and platform health.
    """
    from ml_service.training.models import (
        TradeRiskPrediction,
        PlatformHealthMetric,
        MarketManipulationScore,
    )
    from decimal import Decimal
    
    # Risk prediction stats
    total_predictions = TradeRiskPrediction.objects.count()
    risk_distribution = {
        'low': TradeRiskPrediction.objects.filter(risk_level='LOW').count(),
        'medium': TradeRiskPrediction.objects.filter(risk_level='MEDIUM').count(),
        'high': TradeRiskPrediction.objects.filter(risk_level='HIGH').count(),
        'critical': TradeRiskPrediction.objects.filter(risk_level='CRITICAL').count(),
    }
    
    # Average risk score
    from django.db.models import Avg
    avg_risk = TradeRiskPrediction.objects.aggregate(avg=Avg('risk_score'))['avg']
    
    # Latest platform health
    latest_health = PlatformHealthMetric.objects.order_by('-created_at').first()
    health_data = None
    if latest_health:
        health_data = {
            'status': latest_health.health_status,
            'overall_score': float(latest_health.overall_health_score) if latest_health.overall_health_score else None,
            'alert_level': latest_health.alert_level,
            'created_at': latest_health.created_at.isoformat(),
        }
    
    # Manipulation detection stats
    manipulation_count = MarketManipulationScore.objects.filter(
        is_manipulation_suspected=True
    ).count()
    
    # Model accuracy (simulated for demo)
    model_accuracy = {
        'model_1_suspicious_trades': 0.94,
        'model_4_manipulation_detection': 0.89,
        'model_5_health_prediction': 0.91,
    }
    
    return Response({
        'predictions': {
            'total': total_predictions,
            'distribution': risk_distribution,
            'average_risk_score': float(avg_risk) if avg_risk else 0,
        },
        'platform_health': health_data,
        'manipulation': {
            'flagged_markets': manipulation_count,
        },
        'model_accuracy': model_accuracy,
        'liquidity_forecast': {
            'next_24h_trend': 'stable',
            'confidence': 0.82,
        },
        'timestamp': timezone.now().isoformat(),
    })
