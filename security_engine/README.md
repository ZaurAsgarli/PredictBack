# Security Engine

Security logging and monitoring system for tracking security events, authentication attempts, and enforcing access control.

## Purpose

The security engine provides centralized security event logging, authentication attempt tracking, and admin dashboard data. It does not enforce rate limiting or authentication (those are handled by Django REST Framework), but it logs violations and provides query interfaces.

## Responsibilities

- Store security events in database (`SecurityLog`, `LoginAttempt` models)
- Provide REST API for querying security logs
- Serialize security events for admin dashboard
- Track login attempts with detailed metadata

**Does NOT own**:
- Rate limiting enforcement (Django REST Framework throttling)
- Authentication (Django auth system)
- Authorization/permissions (Django permissions system)
- User blocking (handled by trade execution flow via ML risk assessment)

## RBAC Model

### User Roles

Defined in `backend_api/api/users/models.py:User.Role`:

- `ADMIN`: Full system access (intended for admin users)
- `TRADER`: Standard user (default role)
- `WHALE`: Advanced analytics access (intended for high-value users)
- `BLOCKED`: Blocked users (set by ML auto-ban or manual admin action)

### Role Assignment

- Default: `TRADER` (assigned on user creation)
- Admin: Must be set manually via Django admin or database
- Blocked: Set automatically by trade execution flow when ML risk score > 0.90

### Permission Enforcement

**Current State**: Most admin endpoints use `AllowAny` in development mode.

**Location**: `backend_api/api/admin/views.py` and `security_engine/views.py`

**Endpoints with AllowAny** (must be changed in production):
- `/api/admin/ml-insights/` - `MLInsightsView`
- `/api/admin/deployments/` - `DeploymentLogsView`
- `/api/admin/stats/` - `StatsView`
- `/api/admin/security-logs/` - `SecurityLogsView`
- `/api/admin/security/` - `admin_security()`
- `/api/admin/suspicious/` - `admin_suspicious_users()`
- `/api/admin/ml-insights/` - `admin_ml_insights()`

**Endpoints with IsAuthenticated**:
- `/api/admin/logs/` - `SecurityLogViewSet` (ViewSet, requires authentication)
- `/api/admin/login-attempts/` - `LoginAttemptViewSet` (ViewSet, requires authentication)

**Recommended Production Change**:
```python
# Replace AllowAny with IsAdminUser
permission_classes = [permissions.IsAdminUser]
```

## Enforcement Points

### 1. Rate Limiting

**Enforcement**: Django REST Framework throttling middleware

**Configuration**: `backend_api/core/settings.py:REST_FRAMEWORK`
- Anonymous: 100 requests/hour
- Authenticated: 1000 requests/hour

**Logging**: When rate limit is exceeded:
- HTTP 429 response returned
- Event logged to `SecurityLog` with `event_type='RATE_LIMIT'`
- Severity: `HIGH`
- Logged by: `backend_api/core/utils/middleware/SecurityLoggingMiddleware`

**Location**: Rate limiting is enforced by DRF, not by security_engine. Security_engine only logs violations.

### 2. Authentication

**Enforcement**: Django REST Framework JWT authentication

**Configuration**: `backend_api/core/settings.py:REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']`

**Logging**: Login attempts are logged to `LoginAttempt` model by:
- `backend_api/api/users/views.py:SignUpView` (signup)
- `backend_api/api/users/views.py:LoginView` (login, if implemented)
- Django auth system (if using standard login)

**Location**: Authentication is enforced by DRF, not by security_engine. Security_engine only tracks attempts.

### 3. Authorization

**Enforcement**: Django permissions system + custom role checks

**Current Implementation**:
- Most endpoints use `IsAuthenticated` (any logged-in user)
- Admin endpoints use `AllowAny` (no restriction - development mode)
- No role-based checks in views (roles exist but not enforced)

**Location**: Permission checks are in view classes, not in security_engine.

### 4. ML-Based Auto-Ban

**Enforcement**: Trade execution flow

**Location**: `backend_api/api/trades/views.py:TradeViewSet.create()`

**Logic**:
1. ML risk assessment returns score
2. If score > 0.90: User role set to `BLOCKED`, `is_active=False`
3. Event logged to `SecurityLog` with `event_type='SUSPICIOUS_ACTIVITY'`, `severity='CRITICAL'`

**Not enforced by security_engine**: This is business logic in the trades app.

## What is Centralized vs Trustless

### Centralized (Backend-Controlled)

- User roles (stored in database, set by backend)
- Rate limiting (enforced by backend middleware)
- Security logging (backend writes to database)
- Auto-ban decisions (backend ML assessment)

### Trustless (Blockchain-Controlled)

- None. This is a centralized backend system. Blockchain is used for event indexing only, not for access control.

## What Happens on Rule Violation

### Rate Limit Violation

1. Request exceeds rate limit threshold
2. Django REST Framework returns HTTP 429
3. `SecurityLoggingMiddleware` logs event to `SecurityLog`:
   - `event_type='RATE_LIMIT'`
   - `severity='HIGH'`
   - `ip`: Client IP address
   - `path`: Request path
   - `method`: HTTP method
4. Event also written to file: `backend_api/logs/security/rate_limits.jsonl`

### Failed Login Attempt

1. User submits invalid credentials
2. Django auth system rejects login
3. `LoginAttempt` record created:
   - `success=False`
   - `status='FAILED'`
   - `failure_reason='INVALID_CREDENTIALS'`
   - `email`: Attempted email
   - `ip_address`: Client IP
4. If multiple failures from same IP/email, `is_suspicious=True` may be set (if logic implemented)

### ML Auto-Ban

1. Trade execution triggers ML risk assessment
2. Risk score > 0.90
3. User role set to `BLOCKED`, `is_active=False`
4. `SecurityLog` record created:
   - `event_type='SUSPICIOUS_ACTIVITY'`
   - `severity='CRITICAL'`
   - `user`: Blocked user
   - `message`: "User AUTO-BLOCKED due to high risk score: {score}"
5. Trade is rejected with HTTP 403

### Blocked User Attempts Trade

1. Blocked user attempts to create trade
2. Trade execution checks `user.is_active` and `user.role`
3. Trade rejected (if check implemented)
4. Event may be logged (if logic implemented)

**Note**: Current implementation may not check user role/status before trade execution. ML risk assessment will catch it, but explicit check recommended.

## What is Logged and Why

### SecurityLog Model

**Fields**:
- `timestamp`: When event occurred
- `ip`: Client IP address (for tracking attacks)
- `event_type`: Type of event (`RATE_LIMIT`, `FAILED_LOGIN`, `UNAUTHORIZED_ACCESS`, `SUSPICIOUS_ACTIVITY`)
- `severity`: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
- `message`: Human-readable description
- `path`: Request path (for identifying targeted endpoints)
- `user_agent`: Browser/client identifier (for bot detection)
- `metadata`: JSON field for additional data
- `user`: Foreign key to User (if event is user-specific)

**Logged Events**:
- Rate limit violations (for DDoS detection)
- Failed login attempts (for brute force detection)
- ML auto-ban events (for audit trail)
- Unauthorized access attempts (if implemented)

**Why**: Audit trail for security incidents, compliance, and threat analysis.

### LoginAttempt Model

**Fields**:
- `timestamp`: When attempt occurred
- `email`: Email used in attempt
- `success`: Boolean (successful or failed)
- `status`: `SUCCESS`, `FAILED`, `BLOCKED`
- `failure_reason`: Reason for failure (if failed)
- `ip_address`: Client IP
- `user_agent`: Browser/client identifier
- `is_suspicious`: Boolean flag (for risk scoring)
- `is_bot`: Boolean flag (for bot detection)
- `risk_score`: Numeric risk score (0-100)
- `country`, `city`, `device_type`, `browser`, `os`: Geolocation and device info (if available)

**Logged Events**:
- All login attempts (successful and failed)
- Signup attempts (if logged)

**Why**: Detailed authentication tracking for security analysis, fraud detection, and user behavior analysis.

### Dual Logging

**Database**: Events stored in PostgreSQL (`SecurityLog`, `LoginAttempt` tables)

**File System**: Events also written to JSONL files:
- `backend_api/logs/security/security_events.jsonl`
- `backend_api/logs/security/rate_limits.jsonl`

**Why**: 
- Database: Queryable, indexed, supports admin dashboard
- Files: Fast logging, survives database issues, easy to grep/analyze

## Key Components

### Models

- `security_engine/models.py:SecurityLog`: Security event storage
- `security_engine/models.py:LoginAttempt`: Authentication attempt tracking

### Views

- `security_engine/views.py:SecurityLogViewSet`: REST API for querying security logs
- `security_engine/views.py:LoginAttemptViewSet`: REST API for querying login attempts
- `security_engine/views.py:admin_security()`: Admin dashboard endpoint (uses `AllowAny`)

### Serializers

- `security_engine/serializers.py:SecurityLogSerializer`: Serialize security logs for API
- `security_engine/serializers.py:LoginAttemptSerializer`: Serialize login attempts for API

### Middleware

- `backend_api/core/utils/middleware/SecurityLoggingMiddleware`: Logs security events to database and files

**Location**: Not in security_engine, but uses security_engine models.

## Execution Flow

### Security Event Logging

```
1. Request arrives at Django middleware stack
2. SecurityLoggingMiddleware processes request
3. If rate limit exceeded or security event detected:
   a. Create SecurityLog record in database
   b. Write event to JSONL file
4. Continue request processing
```

### Login Attempt Logging

```
1. User submits login credentials
2. Django auth system validates
3. LoginAttempt record created:
   - success=True if valid, False if invalid
   - IP, user agent, metadata captured
4. If failed: is_suspicious flag may be set (if logic implemented)
```

### Admin Dashboard Query

```
1. Admin requests /api/admin/security/
2. View queries SecurityLog.objects.all().order_by('-timestamp')[:limit]
3. Serialize to JSON with severity color coding
4. Return to frontend
```

## Interfaces

### Called By

- `backend_api/core/utils/middleware/SecurityLoggingMiddleware`: Logs rate limit violations
- `backend_api/api/trades/views.py`: Logs ML auto-ban events
- `backend_api/api/users/views.py`: Logs login attempts (if implemented)
- Admin dashboard frontend: Queries security logs

### Calls

- Django ORM: Database operations
- File system: JSONL log files

## Security / Constraints

### Trust Boundaries

- Security engine is a logging system. It does not enforce security, only records events.
- Admin endpoints are accessible to any user in development (`AllowAny`). Must be restricted in production.

### Assumptions

- Database is available for logging (failures are not logged if DB is down)
- File system is writable for JSONL logs
- Middleware is in correct order in `MIDDLEWARE` setting

### Limits

- No automatic alerting on security events (must be queried manually)
- No automatic IP blocking (must be done manually)
- No rate limiting on security log queries (could be DDoS target)

### Fail-Safe Behavior

- If database write fails, event may be lost (no retry logic)
- If file write fails, event may still be in database
- If middleware fails, request continues (no security impact, but event not logged)

## Production Readiness

### Required Changes

1. **Admin Authentication**: Replace `AllowAny` with `IsAdminUser` in all admin endpoints
2. **Rate Limiting on Auth Endpoints**: Add rate limiting to login/signup endpoints
3. **IP Blocking**: Implement automatic IP blocking for repeated violations
4. **Alerting**: Add real-time alerting for CRITICAL severity events

### Recommended Enhancements

1. **Geolocation**: Populate `country`, `city` fields in `LoginAttempt` from IP
2. **Bot Detection**: Implement bot detection logic to set `is_bot` flag
3. **Risk Scoring**: Implement risk scoring for login attempts
4. **Retention Policy**: Implement log retention and archival

## Related Documentation

- `backend_api/README.md`: Backend architecture
- `backend_api/api/trades/views.py`: ML auto-ban implementation
- `backend_api/core/utils/middleware/SecurityLoggingMiddleware`: Security logging middleware
