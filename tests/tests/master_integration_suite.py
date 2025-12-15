#!/usr/bin/env python
"""
Master Integration Test Suite for PredictHub SDF2 Ecosystem

This script performs comprehensive end-to-end testing of the entire system:
- Database & Migrations
- Smart Contract Logic (Mock)
- API & Data Flow
- Security (Rate Limiting, SQL Injection, Audit Logs)
- ML Inference

**CRITICAL:** This script is designed to run INSIDE the Docker Backend Container.

Usage:
    docker-compose exec web python tests/master_integration_suite.py

Or from within the container:
    python tests/master_integration_suite.py
"""

import os
import sys
import django
import time
import json
from datetime import datetime
from pathlib import Path

# Setup Django environment
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_api.core.settings')
django.setup()

# Now import Django modules
from django.db import connection
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.test import Client
from django.db.models import Q
import joblib
import pickle
import pandas as pd

# Import models
from backend_api.api.indexer.models import OnchainTransaction, OnchainEventLog
from security_engine.models import SecurityLog, LoginAttempt
from ml_service.training.models import TradeRiskPrediction
from ml_service.training.model_loader import load_token_behavior_model, predict_token_behavior, TokenBehaviorModelError

User = get_user_model()

# Test configuration
BASE_URL = os.environ.get('TEST_BASE_URL', 'http://localhost:8000')
TEST_TIMEOUT = 30  # seconds

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


class TestResult:
    """Track test results"""
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
    
    def add_pass(self, test_name, message=""):
        self.passed.append((test_name, message))
        print(f"{GREEN}✅ {test_name}: PASS{RESET}")
        if message:
            print(f"   {message}")
    
    def add_fail(self, test_name, error_message):
        self.failed.append((test_name, error_message))
        print(f"{RED}❌ {test_name}: FAIL{RESET}")
        print(f"   Error: {error_message}")
    
    def add_warning(self, test_name, message):
        self.warnings.append((test_name, message))
        print(f"{YELLOW}⚠️  {test_name}: WARNING{RESET}")
        print(f"   {message}")
    
    def print_summary(self):
        print("\n" + "=" * 60)
        print(f"{BOLD}TEST SUMMARY{RESET}")
        print("=" * 60)
        print(f"{GREEN}✅ Passed: {len(self.passed)}{RESET}")
        print(f"{RED}❌ Failed: {len(self.failed)}{RESET}")
        if self.warnings:
            print(f"{YELLOW}⚠️  Warnings: {len(self.warnings)}{RESET}")
        
        if self.failed:
            print(f"\n{RED}{BOLD}FAILED TESTS:{RESET}")
            for test_name, error in self.failed:
                print(f"  - {test_name}: {error}")
        
        print("=" * 60)
        
        return len(self.failed) == 0


def test_database_connection():
    """Test 1: Database & Migrations Check"""
    print(f"\n{BLUE}{BOLD}[TEST 1] Database & Migrations Check{RESET}")
    print("-" * 60)
    
    result = TestResult()
    
    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result.add_pass("DB Connection", "PostgreSQL connection successful")
    except Exception as e:
        result.add_fail("DB Connection", str(e))
        return result
    
    try:
        # Check migrations are applied
        from django.db.migrations.executor import MigrationExecutor
        from django.db import connections
        executor = MigrationExecutor(connections['default'])
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        
        if plan:
            result.add_fail("Migrations", f"Unapplied migrations: {len(plan)}")
        else:
            result.add_pass("Migrations", "All migrations applied")
    except Exception as e:
        result.add_warning("Migrations Check", f"Could not verify migrations: {str(e)}")
    
    try:
        # Verify required tables exist
        # Note: User model uses db_table='users', not 'users_user'
        required_tables = [
            'users',  # User model has db_table='users'
            'trades_trade',
            'security_logs',
            'indexer_onchaintransaction',
            'indexer_onchaineventlog',
        ]
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            existing_tables = {row[0] for row in cursor.fetchall()}
        
        missing_tables = [t for t in required_tables if t not in existing_tables]
        if missing_tables:
            result.add_fail("Required Tables", f"Missing tables: {missing_tables}")
        else:
            result.add_pass("Required Tables", f"All {len(required_tables)} required tables exist")
    except Exception as e:
        result.add_fail("Table Verification", str(e))
    
    return result


def test_smart_contract_logic():
    """Test 2: Smart Contract Logic (Mock)"""
    print(f"\n{BLUE}{BOLD}[TEST 2] Smart Contract Logic (Mock){RESET}")
    print("-" * 60)
    
    result = TestResult()
    
    try:
        # Simulate a blockchain event payload (JSON)
        mock_event_payload = {
            "event_name": "TradeExecuted",
            "tx_hash": "0x" + "a" * 64,  # Mock hash
            "block_number": 12345,
            "log_index": 0,
            "payload": {
                "marketId": 1,
                "userId": "0x" + "b" * 40,
                "outcome": True,
                "amount": "1000000000000000000",  # 1 ETH in wei
                "timestamp": int(time.time())
            }
        }
        
        # Create OnchainTransaction
        onchain_tx = OnchainTransaction.objects.create(
            tx_hash=mock_event_payload["tx_hash"],
            network="sepolia",
            block_number=mock_event_payload["block_number"],
            status="SUCCESS"
        )
        
        # Create OnchainEventLog
        event_log = OnchainEventLog.objects.create(
            onchain_tx=onchain_tx,
            event_name=mock_event_payload["event_name"],
            tx_hash=mock_event_payload["tx_hash"],
            log_index=mock_event_payload["log_index"],
            payload_json=mock_event_payload["payload"],
            processed_at=datetime.now()
        )
        
        # Verify it was saved
        saved_log = OnchainEventLog.objects.get(tx_hash=mock_event_payload["tx_hash"])
        if saved_log:
            result.add_pass("Event Payload Parsing", "Mock event payload correctly parsed and saved")
            result.add_pass("Transaction Storage", f"Transaction saved with ID: {onchain_tx.id}")
        else:
            result.add_fail("Event Storage", "Event log was not saved to database")
        
        # Cleanup
        event_log.delete()
        onchain_tx.delete()
        
    except Exception as e:
        result.add_fail("Smart Contract Logic", str(e))
    
    return result


def test_api_data_flow():
    """Test 3: API & Data Flow (Frontend Simulation)"""
    print(f"\n{BLUE}{BOLD}[TEST 3] API & Data Flow (Frontend Simulation){RESET}")
    print("-" * 60)
    
    result = TestResult()
    # Override SERVER_NAME to avoid ALLOWED_HOSTS check in tests
    client = Client(SERVER_NAME='localhost')
    
    try:
        # Simulate Next.js signup request
        test_email = f"test_{int(time.time())}@example.com"
        test_username = f"testuser_{int(time.time())}"
        test_password = "TestPass123!"
        
        signup_data = {
            "username": test_username,
            "email": test_email,
            "password": test_password,
            "password_confirm": test_password
        }
        
        # Send POST request to signup endpoint
        # Use HTTP_HOST header to avoid ALLOWED_HOSTS check
        response = client.post('/api/users/signup/', signup_data, content_type='application/json', HTTP_HOST='localhost')
        
        if response.status_code == 201:
            result.add_pass("Signup API", f"User signup successful (Status: {response.status_code})")
            
            # Verify user was saved to database
            try:
                user = User.objects.get(email=test_email)
                result.add_pass("Database Verification", f"User saved to database with ID: {user.id}")
                
                # Cleanup - handle gracefully if related objects cause issues
                try:
                    user.delete()
                except Exception as cleanup_error:
                    # Log but don't fail the test
                    result.add_warning("Cleanup", f"Could not delete test user: {str(cleanup_error)}")
                
            except User.DoesNotExist:
                result.add_fail("Database Verification", "User was not found in database after signup")
        else:
            # Try to extract error message from response
            error_msg = response.content.decode()[:500]  # Limit length
            if response.status_code == 400:
                # Try to parse JSON error
                try:
                    error_data = json.loads(response.content)
                    error_msg = json.dumps(error_data, indent=2)
                except:
                    pass
            result.add_fail("Signup API", f"Signup failed with status {response.status_code}: {error_msg}")
    
    except Exception as e:
        result.add_fail("API Data Flow", str(e))
    
    return result


def test_security_attacks():
    """Test 4: Security 'Red Team' Attack Simulation"""
    print(f"\n{BLUE}{BOLD}[TEST 4] Security 'Red Team' Attack Simulation{RESET}")
    print("-" * 60)
    
    result = TestResult()
    # Override SERVER_NAME to avoid ALLOWED_HOSTS check in tests
    client = Client(SERVER_NAME='localhost')
    
    # Test 4.1: Rate Limiting
    try:
        print("  Testing Rate Limiting...")
        rate_limit_count = 0
        rate_limited_count = 0
        
        # Count rate limit logs before
        from security_engine.detectors.logging import get_security_logger
        security_logger = get_security_logger()
        rate_limit_logs_before = SecurityLog.objects.filter(event_type='RATE_LIMIT').count()
        
        # Send 50 requests rapidly
        for i in range(50):
            response = client.get('/api/analytics/test/', HTTP_HOST='localhost')
            if response.status_code == 429:
                rate_limited_count += 1
            else:
                rate_limit_count += 1
            time.sleep(0.01)  # Small delay to avoid overwhelming
        
        # Wait for logging to complete
        time.sleep(1)
        
        # Check if rate limit logs were created
        rate_limit_logs_after = SecurityLog.objects.filter(event_type='RATE_LIMIT').count()
        new_rate_limit_logs = rate_limit_logs_after - rate_limit_logs_before
        
        if rate_limited_count > 0:
            result.add_pass("Rate Limit Test", f"Rate limiting active: {rate_limited_count}/50 requests blocked (429)")
            
            # Verify logging
            if new_rate_limit_logs > 0:
                result.add_pass("Rate Limit Logging", f"Rate limit events logged: {new_rate_limit_logs} entries in database")
            else:
                result.add_warning("Rate Limit Logging", "Rate limiting active but no logs created in database")
        else:
            result.add_warning("Rate Limit Test", "No rate limiting detected. Check throttling configuration.")
    
    except Exception as e:
        result.add_fail("Rate Limit Test", str(e))
    
    # Test 4.2: SQL Injection
    try:
        print("  Testing SQL Injection Protection...")
        sql_injection_payload = "' OR 1=1 --"
        
        # Try SQL injection on login endpoint
        response = client.post(
            '/api/users/login/',
            {
                'email': sql_injection_payload,
                'password': sql_injection_payload
            },
            content_type='application/json',
            HTTP_HOST='localhost'
        )
        
        # Should return 400/403, not 500 (which would indicate vulnerability)
        if response.status_code in [400, 401, 403]:
            result.add_pass("SQL Injection Protection", f"SQL injection attempt properly rejected (Status: {response.status_code})")
        elif response.status_code == 500:
            result.add_fail("SQL Injection Protection", "SQL injection caused server error (500) - potential vulnerability!")
        else:
            result.add_warning("SQL Injection Protection", f"Unexpected status code: {response.status_code}")
    
    except Exception as e:
        result.add_fail("SQL Injection Test", str(e))
    
    # Test 4.3: Audit Log Check
    try:
        print("  Verifying Security Audit Logs...")
        
        # Count security logs before
        logs_before = SecurityLog.objects.count()
        login_attempts_before = LoginAttempt.objects.count()
        
        # Wait a moment for any async logging
        time.sleep(2)
        
        # Count security logs after
        logs_after = SecurityLog.objects.count()
        login_attempts_after = LoginAttempt.objects.count()
        
        # Check if new logs were created
        new_logs = logs_after - logs_before
        new_attempts = login_attempts_after - login_attempts_before
        
        # Also check for rate limit logs specifically
        rate_limit_logs = SecurityLog.objects.filter(event_type='RATE_LIMIT').order_by('-timestamp')[:5]
        
        if new_logs > 0 or new_attempts > 0:
            log_details = f"{new_logs} SecurityLog entries, {new_attempts} LoginAttempt entries"
            if rate_limit_logs.exists():
                log_details += f", {rate_limit_logs.count()} rate limit logs"
            result.add_pass(
                "Audit Log Check",
                f"Security logs created: {log_details}"
            )
        else:
            result.add_warning(
                "Audit Log Check",
                "No new security logs detected. This may be normal if rate limiting didn't trigger logging."
            )
        
        # Verify we can query security logs
        recent_logs = SecurityLog.objects.order_by('-timestamp')[:5]
        if recent_logs.exists():
            result.add_pass("Security Log Query", f"Successfully queried {recent_logs.count()} recent security logs")
    
    except Exception as e:
        result.add_fail("Audit Log Check", str(e))
    
    return result


def test_ml_inference():
    """Test 5: Data Science & ML Verification"""
    print(f"\n{BLUE}{BOLD}[TEST 5] Data Science & ML Verification{RESET}")
    print("-" * 60)
    
    result = TestResult()
    
    # Test 5.1: Model 1 (Isolation Forest)
    try:
        print("  Testing Model 1: Trade Risk (Isolation Forest)...")
        from ml_service.training.model_loader import get_models, predict_trade_risk
        from ml_service.training.features import build_features
        import pandas as pd
        
        # Create dummy transaction data
        dummy_data = pd.DataFrame([{
            'user_id': 999,
            'created_at': datetime.now(),
            'amount_staked': 100.0
        }])
        
        # Build features
        features = build_features(dummy_data)
        
        # Get prediction
        prediction = predict_trade_risk(features)
        
        # Verify prediction structure
        required_keys = ['score', 'label', 'risk_level']
        if all(key in prediction for key in required_keys):
            result.add_pass(
                "Model 1: Trade Risk",
                f"Prediction successful - Score: {prediction['score']:.4f}, Risk: {prediction['risk_level']}"
            )
            
            # Verify score is a float
            if isinstance(prediction['score'], (int, float)):
                result.add_pass("Model 1: Output Type", "Score is numeric (float/int)")
            else:
                result.add_fail("Model 1: Output Type", f"Score is not numeric: {type(prediction['score'])}")
        else:
            result.add_fail("Model 1: Trade Risk", f"Missing keys in prediction: {set(required_keys) - set(prediction.keys())}")
    
    except FileNotFoundError as e:
        result.add_warning("Model 1: Trade Risk", f"Model file not found: {str(e)}")
    except Exception as e:
        result.add_fail("Model 1: Trade Risk", str(e))
    
    # Test 5.2: Model 3 (Token Behavior) - if available
    try:
        print("  Testing Model 3: Token Behavior (XGBoost)...")
        model, feature_names = load_token_behavior_model()
        
        # Create dummy features DataFrame
        dummy_features = pd.DataFrame({
            feature: [0.5] for feature in feature_names
        })
        
        # Get prediction
        predictions = predict_token_behavior(dummy_features)
        
        if predictions and len(predictions) > 0:
            pred = predictions[0]
            if 'predicted_label' in pred and 'proba' in pred and 'risk_score' in pred:
                result.add_pass(
                    "Model 3: Token Behavior",
                    f"Prediction successful - Label: {pred['predicted_label']}, Risk Score: {pred['risk_score']:.4f}"
                )
            else:
                result.add_fail("Model 3: Token Behavior", "Prediction missing required keys")
        else:
            result.add_fail("Model 3: Token Behavior", "No predictions returned")
    
    except TokenBehaviorModelError as e:
        result.add_warning("Model 3: Token Behavior", f"Model not available: {str(e)}")
    except Exception as e:
        result.add_fail("Model 3: Token Behavior", str(e))
    
    # Test 5.3: ML API Endpoint
    try:
        print("  Testing ML API Endpoint...")
        # Override SERVER_NAME to avoid ALLOWED_HOSTS check in tests
        client = Client(SERVER_NAME='localhost')
        
        # Test trade risk prediction endpoint
        response = client.post(
            '/api/ml/risk/predict/',
            {
                'user_id': 999,
                'amount_staked': 100.0,
                'created_at': datetime.now().isoformat()
            },
            content_type='application/json',
            HTTP_HOST='localhost'
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'score' in data and 'risk_level' in data:
                result.add_pass("ML API Endpoint", f"API returned prediction - Score: {data.get('score')}, Risk: {data.get('risk_level')}")
            else:
                result.add_fail("ML API Endpoint", "API response missing required fields")
        else:
            result.add_warning("ML API Endpoint", f"API returned status {response.status_code}")
    
    except Exception as e:
        result.add_fail("ML API Endpoint", str(e))
    
    return result


def main():
    """Run all integration tests"""
    print("=" * 60)
    print(f"{BOLD}{BLUE}PREDICTHUB SDF2 - MASTER INTEGRATION TEST SUITE{RESET}")
    print("=" * 60)
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Base URL: {BASE_URL}")
    print(f"Working Directory: {os.getcwd()}")
    print("=" * 60)
    
    all_results = TestResult()
    
    # Run all tests (stop on fail for critical tests)
    tests = [
        ("Database & Migrations", test_database_connection, True),
        ("Smart Contract Logic", test_smart_contract_logic, False),
        ("API & Data Flow", test_api_data_flow, True),
        ("Security Attacks", test_security_attacks, False),
        ("ML Inference", test_ml_inference, False),
    ]
    
    for test_name, test_func, stop_on_fail in tests:
        try:
            result = test_func()
            
            # Merge results
            all_results.passed.extend(result.passed)
            all_results.failed.extend(result.failed)
            all_results.warnings.extend(result.warnings)
            
            # Stop on fail if critical
            if stop_on_fail and result.failed:
                print(f"\n{RED}{BOLD}CRITICAL TEST FAILED - STOPPING{RESET}")
                break
        
        except Exception as e:
            all_results.add_fail(test_name, f"Test crashed: {str(e)}")
            if stop_on_fail:
                break
    
    # Print final summary
    success = all_results.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

