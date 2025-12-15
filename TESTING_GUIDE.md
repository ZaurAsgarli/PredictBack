# Master Testing Guide - PredictHub SDF2 Ecosystem

**Complete testing guide for the Dockerized PredictHub platform.**

This guide covers both automated integration testing and manual verification procedures.

**Estimated Time**: 
- Automated Tests: 2-3 minutes
- Manual Verification: 10-15 minutes

---

## 📋 Prerequisites Checklist

Before starting, ensure you have:

- [ ] Docker 20.10+ installed
- [ ] Docker Compose 2.0+ installed
- [ ] Node.js 18+ installed (for smart contract deployment)
- [ ] Smart contract deployed and address in `predicthub_backend/.env`
- [ ] All Docker services running

---

## 🚀 QUICK START: Master Integration Test Suite

### Run Automated E2E Tests

The master integration test suite verifies all layers of the system automatically.

```bash
# Navigate to backend directory
cd predicthub_backend

# Ensure Docker services are running
docker-compose up -d

# Run the master integration test suite
docker-compose exec web python tests/master_integration_suite.py
```

**Expected Output:**
```
============================================================
PREDICTHUB SDF2 - MASTER INTEGRATION TEST SUITE
============================================================
Started at: 2025-01-15T10:30:00
Base URL: http://localhost:8000
Working Directory: /app
============================================================

[TEST 1] Database & Migrations Check
------------------------------------------------------------
✅ DB Connection: PASS
   PostgreSQL connection successful
✅ Migrations: PASS
   All migrations applied
✅ Required Tables: PASS
   All 5 required tables exist

[TEST 2] Smart Contract Logic (Mock)
------------------------------------------------------------
✅ Event Payload Parsing: PASS
   Mock event payload correctly parsed and saved
✅ Transaction Storage: PASS
   Transaction saved with ID: 1

[TEST 3] API & Data Flow (Frontend Simulation)
------------------------------------------------------------
✅ Signup API: PASS
   User signup successful (Status: 201)
✅ Database Verification: PASS
   User saved to database with ID: 123

[TEST 4] Security 'Red Team' Attack Simulation
------------------------------------------------------------
✅ Rate Limit Test: PASS
   Rate limiting active: 25/50 requests blocked (429)
✅ Rate Limit Logging: PASS
   Rate limit events logged: 25 entries in database
✅ SQL Injection Protection: PASS
   SQL injection attempt properly rejected (Status: 400)
✅ Audit Log Check: PASS
   Security logs created: 25 SecurityLog entries, 0 LoginAttempt entries, 25 rate limit logs
✅ Security Log Query: PASS
   Successfully queried 5 recent security logs

[TEST 5] Data Science & ML Verification
------------------------------------------------------------
✅ Model 1: Trade Risk: PASS
   Prediction successful - Score: 0.7500, Risk: LOW
✅ Model 1: Output Type: PASS
   Score is numeric (float/int)
✅ Model 3: Token Behavior: PASS
   Prediction successful - Label: UP, Risk Score: 0.6500
✅ ML API Endpoint: PASS
   API returned prediction - Score: 0.75, Risk: LOW

============================================================
TEST SUMMARY
============================================================
✅ Passed: 12
❌ Failed: 0
⚠️  Warnings: 0
============================================================
```

**✅ All tests passed!** The system is fully functional.

---

## 📖 Interpreting Test Results

### Test Status Indicators

- **✅ PASS**: Test completed successfully
- **❌ FAIL**: Test failed - system issue detected
- **⚠️ WARNING**: Test completed but with concerns (non-critical)

### What Each Test Verifies

#### Test 1: Database & Migrations
- **DB Connection**: Verifies PostgreSQL is accessible
- **Migrations**: Ensures all Django migrations are applied
- **Required Tables**: Checks that core tables exist (`users_user`, `trades_trade`, `security_logs`, etc.)

#### Test 2: Smart Contract Logic (Mock)
- **Event Payload Parsing**: Simulates blockchain event and verifies it's parsed correctly
- **Transaction Storage**: Verifies events are saved to `indexer_onchaintransaction` and `indexer_onchaineventlog` tables

#### Test 3: API & Data Flow
- **Signup API**: Tests user registration endpoint (`POST /api/users/signup/`)
- **Database Verification**: Confirms user data is persisted to database

#### Test 4: Security Attacks
- **Rate Limit Test**: Sends 50 rapid requests and verifies rate limiting (429 responses)
- **Rate Limit Logging**: Verifies rate limit violations are logged to both database and local files
- **SQL Injection Protection**: Attempts SQL injection and verifies proper rejection (400/403, not 500)
- **Audit Log Check**: Verifies security events are logged to `security_logs` table and local JSONL files

#### Test 5: ML Inference
- **Model 1: Trade Risk**: Tests Isolation Forest model prediction
- **Model 3: Token Behavior**: Tests XGBoost token behavior model (if available)
- **ML API Endpoint**: Verifies ML predictions are accessible via REST API

---

## 🔍 Manual Verification Procedures

### SECTION 1: Database Verification

#### Check Database Connection

```bash
docker-compose exec web python manage.py dbshell
```

**In psql:**
```sql
-- Verify connection
SELECT version();

-- Check tables exist
\dt

-- Check migrations
SELECT * FROM django_migrations ORDER BY applied DESC LIMIT 10;

-- Exit
\q
```

#### Verify Required Tables

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;
```

**Expected Tables:**
- `users_user`
- `trades_trade`
- `security_logs`
- `indexer_onchaintransaction`
- `indexer_onchaineventlog`
- `ml_traderiskprediction`
- And others...

---

### SECTION 2: API Endpoint Testing

#### Test User Signup

```bash
curl -X POST http://localhost:8000/api/users/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPass123!",
    "password_confirm": "TestPass123!"
  }'
```

**Expected Response:**
```json
{
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com"
  },
  "tokens": {
    "refresh": "...",
    "access": "..."
  }
}
```

#### Verify User in Database

```bash
docker-compose exec web python manage.py shell
```

```python
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.get(email='test@example.com')
print(f"User ID: {user.id}, Username: {user.username}")
```

---

### SECTION 3: Security Testing

#### Test Rate Limiting

```bash
# Send 50 rapid requests
for i in {1..50}; do
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/analytics/test/
done
```

**Expected:** Some requests should return `429 Too Many Requests`

#### Verify Rate Limit Logging

After triggering rate limits, verify that events are logged:

**1. Check Database Logs:**
```bash
docker-compose exec web python manage.py shell
```

```python
from security.models import SecurityLog
from django.utils import timezone
from datetime import timedelta

# Get recent rate limit logs
recent = timezone.now() - timedelta(minutes=5)
rate_limits = SecurityLog.objects.filter(
    event_type='RATE_LIMIT',
    timestamp__gte=recent
).order_by('-timestamp')

print(f"Found {rate_limits.count()} rate limit violations")
for log in rate_limits[:5]:
    print(f"  {log.timestamp} - {log.ip} - {log.path} - {log.method}")
```

**2. Check Local File Logs:**
```bash
# View rate limit log file
docker-compose exec web cat LOGS/security/rate_limits.jsonl | tail -20

# Count rate limit violations
docker-compose exec web grep -c "RATE_LIMIT" LOGS/security/rate_limits.jsonl

# View as formatted JSON
docker-compose exec web tail -5 LOGS/security/rate_limits.jsonl | python -m json.tool
```

**Expected Output:**
```json
{
  "timestamp": "2025-12-02T19:11:33.123456Z",
  "event_type": "RATE_LIMIT",
  "severity": "HIGH",
  "ip_address": "127.0.0.1",
  "path": "/api/analytics/test/",
  "method": "GET",
  "message": "Rate limit exceeded for GET /api/analytics/test/ from 127.0.0.1"
}
```

#### Test SQL Injection Protection

```bash
curl -X POST http://localhost:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "' OR 1=1 --",
    "password": "' OR 1=1 --"
  }'
```

**Expected:** Status `400` or `401`, **NOT** `500`

#### View Security Logs

**Via API:**
```bash
# Get all security logs
curl http://localhost:8000/api/admin/security-logs/

# Get statistics
curl http://localhost:8000/api/admin/logs/stats/

# Filter by event type (rate limits)
curl "http://localhost:8000/api/admin/logs/?event_type=RATE_LIMIT"

# Filter by severity
curl "http://localhost:8000/api/admin/logs/?severity=HIGH"
```

**Via Database:**
```sql
-- View recent rate limit violations
SELECT 
    timestamp,
    ip,
    event_type,
    severity,
    path,
    message
FROM security_logs
WHERE event_type = 'RATE_LIMIT'
ORDER BY timestamp DESC
LIMIT 10;

-- Count rate limit violations by IP
SELECT 
    ip,
    COUNT(*) as violation_count
FROM security_logs
WHERE event_type = 'RATE_LIMIT'
GROUP BY ip
ORDER BY violation_count DESC;
```

**Via Local Files:**
```bash
# View all security events
docker-compose exec web cat LOGS/security/security_events.jsonl | tail -50

# View rate limit logs specifically
docker-compose exec web cat LOGS/security/rate_limits.jsonl | tail -20

# Count events by type
docker-compose exec web grep -o '"event_type":"[^"]*"' LOGS/security/security_events.jsonl | sort | uniq -c
```

---

### SECTION 4: ML Model Testing

#### Test Model 1: Trade Risk Prediction

```bash
curl -X POST http://localhost:8000/api/ml/risk/predict/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "amount_staked": 100.0,
    "created_at": "2025-01-15T10:00:00Z"
  }'
```

**Expected Response:**
```json
{
  "score": 0.75,
  "label": 1,
  "risk_level": "LOW"
}
```

#### Verify ML Prediction in Database

```sql
SELECT 
    id,
    user_id,
    score,
    label,
    risk_level,
    created_at
FROM ml_traderiskprediction
ORDER BY created_at DESC
LIMIT 5;
```

#### Test Model 3: Token Behavior Forecast

```bash
curl "http://localhost:8000/api/ml/token-behavior/market/1/?window_hours=24"
```

**Expected Response:**
```json
{
  "market_id": 1,
  "window_hours": 24,
  "predictions": [
    {
      "timestamp": "2025-01-15T10:00:00",
      "predicted_label": "UP",
      "proba": {
        "DOWN": 0.2,
        "FLAT": 0.3,
        "UP": 0.5
      },
      "risk_score": 0.5
    }
  ],
  "kpis": {
    "total_predictions": 1,
    "up_count": 1,
    "avg_risk_score": 0.5
  }
}
```

---

### SECTION 5: Smart Contract Integration

#### Verify Indexer is Running

```bash
# Check indexer logs
docker-compose logs indexer | tail -20

# Check indexer status via JSON-RPC
curl -X POST http://localhost:8000/api/indexer/rpc/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "get_indexer_status",
    "params": {},
    "id": 1
  }'
```

#### Check Indexed Events

```sql
SELECT 
    event_name,
    block_number,
    tx_hash,
    created_at
FROM indexer_onchaineventlog
ORDER BY created_at DESC
LIMIT 10;
```

---

## 🎯 Viewing Security Dashboard

### Via API

```bash
# Get all security logs
curl http://localhost:8000/api/admin/security-logs/

# Get statistics
curl http://localhost:8000/api/admin/logs/stats/

# Filter by severity
curl "http://localhost:8000/api/admin/logs/?severity=HIGH"
```

### Via Admin Panel

1. Open browser: http://localhost:8000/admin/
2. Navigate to: **Security → Security logs**
3. View recent security events

### Via Database

```sql
-- Recent security events
SELECT 
    timestamp,
    ip,
    event_type,
    severity,
    message
FROM security_logs
ORDER BY timestamp DESC
LIMIT 20;

-- Event type statistics
SELECT 
    event_type,
    COUNT(*) as count
FROM security_logs
GROUP BY event_type
ORDER BY count DESC;

-- Severity breakdown
SELECT 
    severity,
    COUNT(*) as count
FROM security_logs
GROUP BY severity;
```

---

## 🎯 Viewing ML Results

### Via API

```bash
# Platform Health (Model 5)
curl http://localhost:8000/api/ml/health/

# Market Manipulation Analysis (Model 4)
curl http://localhost:8000/api/ml/manipulation/market/1/

# Token Behavior Forecast (Model 3)
curl http://localhost:8000/api/ml/token-behavior/market/1/
```

### Via Database

```sql
-- Recent ML predictions
SELECT 
    id,
    user_id,
    score,
    label,
    risk_level,
    created_at
FROM ml_traderiskprediction
ORDER BY created_at DESC
LIMIT 10;

-- Prediction statistics
SELECT 
    risk_level,
    COUNT(*) as count,
    AVG(score) as avg_score
FROM ml_traderiskprediction
GROUP BY risk_level;
```

---

## 🐛 Troubleshooting

### Master Integration Suite Fails

**Issue: Database connection fails**
```bash
# Check if database is running
docker-compose ps db

# Check database logs
docker-compose logs db

# Restart database
docker-compose restart db
```

**Issue: Migrations not applied**
```bash
# Apply migrations
docker-compose exec web python manage.py migrate
```

**Issue: ML models not found**
```bash
# Check if model files exist
docker-compose exec web ls -la ml/models/

# Expected files:
# - isolation_forest.pkl
# - feature_scaler.pkl
# - model3_token_xgb.pkl (optional)
# - model3_token_xgb_features.pkl (optional)
```

### API Endpoints Not Responding

**Check if web service is running:**
```bash
docker-compose ps web
docker-compose logs web | tail -50
```

**Restart web service:**
```bash
docker-compose restart web
```

### Security Tests Fail

**Rate limiting not working:**
- Check `REST_FRAMEWORK` settings in `config/settings.py`
- Verify throttling classes are configured

**Security logs not appearing:**
- Check `security` app is in `INSTALLED_APPS`
- Verify migrations are applied: `python manage.py migrate security`
- Check security logging configuration

---

## 📊 Expected Test Results

After running the master integration suite, you should see:

| Test Category | Expected Result |
|---------------|----------------|
| Database & Migrations | ✅ All PASS |
| Smart Contract Logic | ✅ All PASS |
| API & Data Flow | ✅ All PASS |
| Security Attacks | ✅ Rate Limit: PASS, SQL Injection: PASS, Audit Log: PASS |
| ML Inference | ✅ Model 1: PASS, ML API: PASS |

**Warnings are acceptable** for:
- Model 3 (if model files not present)
- Some security tests (if rate limiting not configured)

---

## 🔗 Quick Reference

### Docker Commands

```bash
# Start all services
cd predicthub_backend
docker-compose up -d

# Run integration tests
docker-compose exec web python tests/master_integration_suite.py

# View logs
docker-compose logs -f web
docker-compose logs -f indexer

# Execute Django commands
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py shell
```

### Key URLs

- API Root: http://localhost:8000/
- Swagger: http://localhost:8000/swagger/
- Admin: http://localhost:8000/admin/
- Security Logs: http://localhost:8000/api/admin/security-logs/
- GraphQL: http://localhost:8000/graphql/

### Key SQL Queries

```sql
-- Check indexed events
SELECT COUNT(*) FROM indexer_onchaineventlog;

-- Check ML predictions
SELECT COUNT(*) FROM ml_traderiskprediction;

-- Check security logs
SELECT COUNT(*) FROM security_logs;

-- Recent security events
SELECT * FROM security_logs ORDER BY timestamp DESC LIMIT 10;
```

---

## ✅ Success Criteria

**System is working correctly if:**

1. ✅ Master integration suite shows all critical tests PASS
2. ✅ Database connection successful
3. ✅ All migrations applied
4. ✅ API endpoints respond correctly
5. ✅ Security features active (rate limiting, logging)
6. ✅ ML models load and make predictions
7. ✅ Security logs are being created

**If all criteria are met, the SDF2 system is fully functional!** 🎉

---

## 📚 Next Steps

- **Production Deployment**: See `predicthub_backend/README.md`
- **API Documentation**: http://localhost:8000/swagger/
- **Admin Panel**: http://localhost:8000/admin/
- **Monitoring**: Use JSON-RPC endpoint for health checks

---

**End of Testing Guide** ✅
