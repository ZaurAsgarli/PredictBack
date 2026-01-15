from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from ml_service.training.models import TradeRiskPrediction
from django.conf import settings
import os
import json
from pathlib import Path

class MLInsightsView(APIView):
    """
    GET /api/admin/ml-insights/
    Returns recent risk predictions for the Admin Dashboard.
    """
    permission_classes = [permissions.AllowAny] # For demo simplicity, ideally IsAdminUser

    def get(self, request):
        # 1. Fetch recent predictions
        recent = TradeRiskPrediction.objects.all().order_by('-created_at')[:20]
        
        data = []
        for p in recent:
            data.append({
                "id": p.id,
                "timestamp": p.created_at.isoformat(),
                "user_id": p.user_id,
                "score": p.score,
                "risk_level": p.risk_level,
                "label": "BLOCKED" if p.score > 0.85 else ("SUSPICIOUS" if p.score > 0.5 else "APPROVED"), 
                # ^ Heuristic mapping based on our Circuit Breaker logic
                "market_id": p.market_id
            })
            
        # 2. Calculate simple stats
        total = TradeRiskPrediction.objects.count()
        blocked = TradeRiskPrediction.objects.filter(score__gt=0.85).count()
        
        return Response({
            "recent_predictions": data,
            "metrics": {
                "total_analyzed": total,
                "blocked_attacks": blocked,
                "block_rate": (blocked/total) if total > 0 else 0
            }
        })

class DeploymentLogsView(APIView):
    """
    GET /api/admin/deployments/
    Reads the local deployment log file.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Handle path correctly relative to BASE_DIR
        # BASE_DIR is usually backend_api
        # Log is at ../smart_contracts/logs/deployment_history.log
        log_path = Path(settings.BASE_DIR).parent / 'smart_contracts' / 'logs' / 'deployment_history.log'
        
        if not log_path.exists():
            # Fallback check
            log_path = Path(settings.BASE_DIR) / 'smart_contracts' / 'logs' / 'deployment_history.log'
        
        if not log_path.exists():
             return Response({'entries': [f"Log not found at {log_path}"]})
            
        try:
            with open(log_path, 'r') as f:
                lines = f.readlines()
                # Return last 50 lines reversed
                return Response({'entries': [l.strip() for l in reversed(lines[-50:])]})
        except Exception as e:
            return Response({'error': str(e)}, status=500)

class StatsView(APIView):
    """General system stats (Markets, Users)"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from backend_api.api.markets.models import Market
        from backend_api.api.users.models import User
        
        active = Market.objects.filter(status='active').count()
        resolved = Market.objects.filter(status='resolved').count()
        total_users = User.objects.count()
        
        return Response({
            'markets': {
                'active': active,
                'resolved': resolved,
                'total': active + resolved
            },
            'users': {
                'total': total_users
            }
        })

class SecurityLogsView(APIView):
    """Security Event Logs"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from security_engine.models import SecurityLog
        logs = SecurityLog.objects.order_by('-timestamp')[:20]
        data = [{
            'id': l.id,
            'event_type': l.event_type,
            'severity': l.severity,
            'description': l.message or l.description, # Handle inconsistent naming if any
            'timestamp': l.timestamp.isoformat() if l.timestamp else None,
            'ip': l.ip_address or l.ip
        } for l in logs]
        return Response({'logs': data})
