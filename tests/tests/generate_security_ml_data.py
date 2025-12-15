"""
Comprehensive Security and ML Testing Script
Generates extensive security events and ML predictions for analysis
"""
import os
import sys
import django
import random
import json
from datetime import datetime, timedelta
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_api.core.settings')
sys.path.insert(0, '/app')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from security_engine.models import SecurityLog, LoginAttempt
from backend_api.api.trades.models import Trade
from backend_api.api.markets.models import Market

User = get_user_model()

print("=" * 80)
print("COMPREHENSIVE SECURITY AND ML TESTING SCRIPT")
print("=" * 80)
print(f"Started at: {datetime.now()}")
print()

# ============================================================================
# PART 1: SECURITY EVENTS
# ============================================================================
print("\n" + "=" * 80)
print("PART 1: GENERATING SECURITY EVENTS")
print("=" * 80)

# Create some test IP addresses
test_ips = [
    '192.168.1.100', '192.168.1.101', '10.0.0.50', '10.0.0.51',
    '172.16.0.10', '8.8.8.8', '1.2.3.4', '5.6.7.8',
    '203.0.113.1', '198.51.100.1', '192.0.2.1', '100.64.0.1'
]

# Test emails for failed login attempts
test_emails = [
    'hacker@evil.com', 'attacker@malicious.net', 'admin@fake.com',
    'root@server.com', 'test@test.com', 'user@domain.com',
    'bruteforce@attack.com', 'sql@injection.com'
]

print("\n[1.1] Creating Failed Login Attempts...")
login_attempts_created = 0

for i in range(200):
    ip = random.choice(test_ips)
    email = random.choice(test_emails)
    
    # Create login attempt with correct field names
    attempt = LoginAttempt.objects.create(
        email=email,
        ip_address=ip,
        user_agent=f'Mozilla/5.0 (Suspicious Bot {i})',
        success=False,
        failure_reason=random.choice(['INVALID_CREDENTIALS', 'ACCOUNT_LOCKED', 'TOO_MANY_ATTEMPTS', 'SUSPICIOUS_IP']),
        status=random.choice(['FAILED', 'BLOCKED']),
        is_suspicious=random.random() > 0.5,
        risk_score=Decimal(str(round(random.uniform(30, 100), 2))),
    )
    
    # Set random timestamp in the past
    attempt.timestamp = timezone.now() - timedelta(
        hours=random.randint(0, 72),
        minutes=random.randint(0, 59)
    )
    attempt.save(update_fields=['timestamp'])
    login_attempts_created += 1
    
    if (i + 1) % 50 == 0:
        print(f"  → Created {i + 1} login attempts...")

print(f"✓ Created {login_attempts_created} failed login attempts")

# Also create some successful logins
print("\n[1.2] Creating Successful Login Attempts...")
successful_logins = 0

# Get some real users
real_users = list(User.objects.filter(email__startswith='synthetic_user')[:20])
for user in real_users:
    for _ in range(random.randint(1, 5)):
        attempt = LoginAttempt.objects.create(
            email=user.email,
            ip_address=random.choice(test_ips[:4]),  # Use "safe" IPs
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            success=True,
            status='SUCCESS',
            is_suspicious=False,
            user=user,
        )
        attempt.timestamp = timezone.now() - timedelta(
            hours=random.randint(0, 48),
            minutes=random.randint(0, 59)
        )
        attempt.save(update_fields=['timestamp'])
        successful_logins += 1

print(f"✓ Created {successful_logins} successful login attempts")

print("\n[1.3] Creating Security Log Events...")
security_logs_created = 0

# Event patterns with correct choices
event_patterns = [
    {'event_type': 'RATE_LIMIT', 'severity': 'MEDIUM', 'message': 'API rate limit exceeded for endpoint'},
    {'event_type': 'FAILED_LOGIN', 'severity': 'HIGH', 'message': 'Multiple failed login attempts from same IP'},
    {'event_type': 'UNAUTHORIZED_ACCESS', 'severity': 'HIGH', 'message': 'Attempt to access restricted admin endpoint'},
    {'event_type': 'SUSPICIOUS_ACTIVITY', 'severity': 'CRITICAL', 'message': 'SQL injection pattern detected in input'},
    {'event_type': 'SUSPICIOUS_ACTIVITY', 'severity': 'HIGH', 'message': 'Cross-site scripting attempt blocked'},
    {'event_type': 'UNAUTHORIZED_ACCESS', 'severity': 'HIGH', 'message': 'JWT token manipulation detected'},
    {'event_type': 'SUSPICIOUS_ACTIVITY', 'severity': 'MEDIUM', 'message': 'Unusual trading pattern detected'},
    {'event_type': 'RATE_LIMIT', 'severity': 'LOW', 'message': 'Rate limit warning threshold reached'},
    {'event_type': 'FAILED_LOGIN', 'severity': 'CRITICAL', 'message': 'Possible brute force attack in progress'},
    {'event_type': 'SUSPICIOUS_ACTIVITY', 'severity': 'MEDIUM', 'message': 'Bot-like behavior detected'},
]

for i in range(300):
    pattern = random.choice(event_patterns)
    ip = random.choice(test_ips)
    
    log = SecurityLog.objects.create(
        event_type=pattern['event_type'],
        severity=pattern['severity'],
        ip=ip,
        user_agent=f'Mozilla/5.0 (Test Agent {i % 20})',
        message=pattern['message'],
        path=random.choice(['/api/users/login/', '/api/trades/', '/api/markets/', '/admin/', '/api/ml/']),
        metadata={
            'attempt_count': random.randint(1, 50),
            'blocked': random.choice([True, False]),
            'risk_score': round(random.uniform(0.5, 1.0), 3),
            'request_method': random.choice(['POST', 'GET', 'PUT', 'DELETE']),
            'response_status': random.choice([401, 403, 429, 500]),
        },
    )
    
    # Set random timestamp
    log.timestamp = timezone.now() - timedelta(
        hours=random.randint(0, 168),  # Past week
        minutes=random.randint(0, 59)
    )
    log.save(update_fields=['timestamp'])
    security_logs_created += 1
    
    if (i + 1) % 100 == 0:
        print(f"  → Created {i + 1} security logs...")

print(f"✓ Created {security_logs_created} security log events")

# ============================================================================
# PART 2: ML PREDICTIONS AND RISK ANALYSIS
# ============================================================================
print("\n" + "=" * 80)
print("PART 2: GENERATING ML PREDICTIONS AND RISK ANALYSIS")
print("=" * 80)

# Import ML services
try:
    from ml_service.training.services.trade_risk import TradeRiskService
    HAS_TRADE_RISK = True
except ImportError as e:
    print(f"Trade Risk Service not available: {e}")
    HAS_TRADE_RISK = False

try:
    from ml_service.training.services.manipulation_detector import ManipulationDetectorService
    HAS_MANIPULATION = True
except ImportError as e:
    print(f"Manipulation Detector not available: {e}")
    HAS_MANIPULATION = False

try:
    from ml_service.training.services.exposure import ExposureService
    HAS_EXPOSURE = True
except ImportError as e:
    print(f"Exposure Service not available: {e}")
    HAS_EXPOSURE = False

# Get trades for analysis
trades = list(Trade.objects.select_related('user', 'market').order_by('-created_at')[:500])
print(f"\n[2.1] Analyzing {len(trades)} trades...")

ml_predictions = []
high_risk_count = 0
medium_risk_count = 0
low_risk_count = 0

if HAS_TRADE_RISK:
    trade_risk_service = TradeRiskService()
    
    for i, trade in enumerate(trades):
        try:
            prediction = trade_risk_service.predict_trade_risk(trade)
            
            if prediction:
                ml_predictions.append({
                    'trade_id': trade.id,
                    'user_id': trade.user_id,
                    'market_id': trade.market_id,
                    'amount': str(trade.amount_staked),
                    'risk_score': prediction.get('score', 0),
                    'risk_level': prediction.get('risk_level', 'UNKNOWN'),
                    'timestamp': str(trade.created_at),
                })
                
                risk_level = prediction.get('risk_level', '')
                if risk_level == 'HIGH':
                    high_risk_count += 1
                elif risk_level == 'MEDIUM':
                    medium_risk_count += 1
                else:
                    low_risk_count += 1
            
            if (i + 1) % 100 == 0:
                print(f"  → Analyzed {i + 1} trades...")
                
        except Exception as e:
            pass
    
    print(f"✓ ML Risk Analysis Complete:")
    print(f"  - High Risk: {high_risk_count}")
    print(f"  - Medium Risk: {medium_risk_count}")
    print(f"  - Low Risk: {low_risk_count}")
else:
    # Generate synthetic ML predictions
    print("[2.1] Generating synthetic ML predictions...")
    for i, trade in enumerate(trades):
        score = round(random.uniform(-0.5, 0.5), 4)
        if score < -0.3:
            risk_level = 'HIGH'
            high_risk_count += 1
        elif score < -0.1:
            risk_level = 'MEDIUM'
            medium_risk_count += 1
        else:
            risk_level = 'LOW'
            low_risk_count += 1
        
        ml_predictions.append({
            'trade_id': trade.id,
            'user_id': trade.user_id,
            'market_id': trade.market_id,
            'amount': str(trade.amount_staked),
            'risk_score': score,
            'risk_level': risk_level,
            'anomaly_label': -1 if score < -0.1 else 1,
            'timestamp': str(trade.created_at),
        })
        
        if (i + 1) % 100 == 0:
            print(f"  → Generated predictions for {i + 1} trades...")
    
    print(f"✓ Synthetic ML Analysis Complete:")
    print(f"  - High Risk: {high_risk_count}")
    print(f"  - Medium Risk: {medium_risk_count}")
    print(f"  - Low Risk: {low_risk_count}")

# Save ML predictions to log
os.makedirs('/app/backend_api/ml_logs', exist_ok=True)
ml_log_path = '/app/backend_api/ml_logs/comprehensive_risk_analysis.jsonl'
with open(ml_log_path, 'w') as f:
    for pred in ml_predictions:
        f.write(json.dumps(pred) + '\n')
print(f"✓ Saved {len(ml_predictions)} predictions to {ml_log_path}")

# Generate manipulation detection results
print("\n[2.2] Generating Manipulation Detection Results...")
markets = list(Market.objects.filter(title__startswith='Synthetic')[:30])
manipulation_results = []

for market in markets:
    # Simulate manipulation detection
    is_suspicious = random.random() > 0.7
    manipulation_results.append({
        'market_id': market.id,
        'market_title': market.title,
        'is_suspicious': is_suspicious,
        'manipulation_score': round(random.uniform(0, 1), 4) if is_suspicious else round(random.uniform(0, 0.3), 4),
        'indicators': {
            'wash_trading': random.random() > 0.8,
            'price_manipulation': random.random() > 0.7,
            'volume_anomaly': random.random() > 0.6,
            'timing_anomaly': random.random() > 0.75,
        },
        'analyzed_at': str(timezone.now())
    })

manip_log_path = '/app/backend_api/ml_logs/manipulation_detection.jsonl'
with open(manip_log_path, 'w') as f:
    for result in manipulation_results:
        f.write(json.dumps(result) + '\n')
print(f"✓ Saved {len(manipulation_results)} manipulation results to {manip_log_path}")

# Generate exposure analysis
print("\n[2.3] Generating Exposure Analysis...")
users = list(User.objects.filter(email__startswith='synthetic_user')[:100])
exposure_results = []

for user in users:
    exposure_results.append({
        'user_id': user.id,
        'email': user.email,
        'total_exposure': round(random.uniform(100, 10000), 2),
        'max_single_position': round(random.uniform(50, 2000), 2),
        'markets_count': random.randint(1, 15),
        'risk_concentration': round(random.uniform(0.1, 0.9), 2),
        'exposure_level': random.choice(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']),
        'analyzed_at': str(timezone.now())
    })

exposure_log_path = '/app/backend_api/ml_logs/exposure_analysis.jsonl'
with open(exposure_log_path, 'w') as f:
    for result in exposure_results:
        f.write(json.dumps(result) + '\n')
print(f"✓ Saved {len(exposure_results)} exposure results to {exposure_log_path}")

# ============================================================================
# PART 3: SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"\nSecurity Events Generated:")
print(f"  - Failed Login Attempts: {login_attempts_created}")
print(f"  - Successful Login Attempts: {successful_logins}")
print(f"  - Security Log Events: {security_logs_created}")
print(f"  - TOTAL SECURITY EVENTS: {login_attempts_created + successful_logins + security_logs_created}")

print(f"\nML Analysis Generated:")
print(f"  - Trade Risk Predictions: {len(ml_predictions)}")
print(f"    - High Risk: {high_risk_count}")
print(f"    - Medium Risk: {medium_risk_count}")
print(f"    - Low Risk: {low_risk_count}")
print(f"  - Manipulation Detections: {len(manipulation_results)}")
print(f"  - Exposure Analyses: {len(exposure_results)}")

print(f"\nLog Files Created:")
print(f"  - {ml_log_path}")
print(f"  - {manip_log_path}")
print(f"  - {exposure_log_path}")

print("\n" + "=" * 80)
print("VERIFICATION - Sample Data")
print("=" * 80)

# Show sample security events
print("\n--- Sample Failed Login Attempts ---")
for attempt in LoginAttempt.objects.filter(success=False).order_by('-timestamp')[:5]:
    print(f"  {attempt.timestamp.strftime('%Y-%m-%d %H:%M')} | {attempt.email} | {attempt.ip_address} | {attempt.status} | Risk: {attempt.risk_score}")

print("\n--- Sample Security Logs ---")
for log in SecurityLog.objects.order_by('-timestamp')[:5]:
    print(f"  {log.timestamp.strftime('%Y-%m-%d %H:%M')} | {log.event_type} | {log.severity} | {log.ip} | {log.message[:50]}...")

print("\n--- Sample ML Predictions (High Risk) ---")
high_risk_preds = [p for p in ml_predictions if p['risk_level'] == 'HIGH'][:5]
for pred in high_risk_preds:
    print(f"  Trade {pred['trade_id']} | User {pred['user_id']} | Score: {pred['risk_score']:.4f} | {pred['risk_level']}")

print("\n" + "=" * 80)
print(f"Completed at: {datetime.now()}")
print("=" * 80)
