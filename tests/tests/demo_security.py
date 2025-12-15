#!/usr/bin/env python
"""
Docker-compatible security test script.

This script tests the security logging functionality by:
1. Sending 50 fast requests to trigger rate limiting (429)
2. Sending 5 failed login attempts (401)
3. Verifying that SecurityLogs entries were created
4. Reporting the results

Run this script inside the Docker container:
    docker-compose exec web python tests/demo_security.py
"""
import os
import sys
import django
import time
import requests
from datetime import datetime

# Setup Django environment
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from security_engine.models import SecurityLog


def get_client_ip():
    """Get the client IP (for Docker, this will be the container's IP)"""
    try:
        response = requests.get('http://httpbin.org/ip', timeout=2)
        return response.json().get('origin', '127.0.0.1')
    except:
        return '127.0.0.1'


def test_rate_limiting(base_url='http://localhost:8000'):
    """
    Send 50 fast requests to trigger rate limiting.
    Uses the test endpoint at /api/analytics/test/
    """
    print("\n" + "="*60)
    print("PHASE 1: Testing Rate Limiting")
    print("="*60)
    
    test_url = f"{base_url}/api/analytics/test/"
    rate_limit_count = 0
    success_count = 0
    
    print(f"Sending 50 requests to {test_url}...")
    
    for i in range(50):
        try:
            response = requests.get(test_url, timeout=2)
            if response.status_code == 429:
                rate_limit_count += 1
            elif response.status_code == 200:
                success_count += 1
        except Exception as e:
            print(f"Request {i+1} failed: {e}")
        
        # Small delay to avoid overwhelming the server too quickly
        time.sleep(0.1)
    
    print(f"✅ Completed: {success_count} successful, {rate_limit_count} rate limited")
    return rate_limit_count


def test_failed_logins(base_url='http://localhost:8000'):
    """
    Send 5 failed login attempts.
    """
    print("\n" + "="*60)
    print("PHASE 2: Testing Failed Login Detection")
    print("="*60)
    
    login_url = f"{base_url}/api/users/login/"
    failed_count = 0
    
    print(f"Sending 5 failed login attempts to {login_url}...")
    
    for i in range(5):
        try:
            response = requests.post(
                login_url,
                json={
                    'email': f'fake_user_{i}@example.com',
                    'password': 'wrong_password_12345'
                },
                timeout=2
            )
            if response.status_code == 401:
                failed_count += 1
        except Exception as e:
            print(f"Login attempt {i+1} failed: {e}")
        
        time.sleep(0.2)
    
    print(f"✅ Completed: {failed_count} failed login attempts sent")
    return failed_count


def verify_security_logs():
    """
    Verify that SecurityLogs entries were created in the database.
    """
    print("\n" + "="*60)
    print("PHASE 3: Verifying Security Logs in Database")
    print("="*60)
    
    # Get logs created in the last minute
    from django.utils import timezone
    from datetime import timedelta
    
    recent_time = timezone.now() - timedelta(minutes=2)
    recent_logs = SecurityLog.objects.filter(timestamp__gte=recent_time)
    
    rate_limit_logs = recent_logs.filter(event_type='RATE_LIMIT')
    failed_login_logs = recent_logs.filter(event_type='FAILED_LOGIN')
    
    print(f"Total recent security logs: {recent_logs.count()}")
    print(f"  - Rate Limit violations: {rate_limit_logs.count()}")
    print(f"  - Failed Login attempts: {failed_login_logs.count()}")
    
    # Show sample logs
    if rate_limit_logs.exists():
        print("\nSample Rate Limit Logs:")
        for log in rate_limit_logs[:3]:
            print(f"  - {log.timestamp} | {log.ip} | {log.event_type} | {log.severity}")
    
    if failed_login_logs.exists():
        print("\nSample Failed Login Logs:")
        for log in failed_login_logs[:3]:
            print(f"  - {log.timestamp} | {log.ip} | {log.event_type} | {log.severity}")
    
    return {
        'total': recent_logs.count(),
        'rate_limit': rate_limit_logs.count(),
        'failed_login': failed_login_logs.count()
    }


def main():
    """
    Main test execution function.
    """
    print("\n" + "="*60)
    print("SECURITY LOGGING TEST SCRIPT")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Testing against: http://localhost:8000")
    
    # Run tests
    rate_limit_count = test_rate_limiting()
    failed_login_count = test_failed_logins()
    
    # Wait a moment for logs to be written
    print("\nWaiting 2 seconds for logs to be written to database...")
    time.sleep(2)
    
    # Verify logs
    stats = verify_security_logs()
    
    # Final report
    print("\n" + "="*60)
    print("FINAL REPORT")
    print("="*60)
    
    total_alerts = stats['rate_limit'] + stats['failed_login']
    
    if total_alerts > 0:
        print(f"✅ SUCCESS: Dashboard has received {total_alerts} security alerts!")
        print(f"   - Rate Limit violations: {stats['rate_limit']}")
        print(f"   - Failed Login attempts: {stats['failed_login']}")
        print(f"\n📊 View logs at: http://localhost:8000/api/admin/security-logs/")
        print(f"📊 Admin panel: http://localhost:8000/admin/security/securitylog/")
        return 0
    else:
        print("❌ FAILURE: No security logs were created!")
        print("   This may indicate:")
        print("   - Middleware is not working correctly")
        print("   - Database connection issues")
        print("   - Rate limiting is not configured")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

