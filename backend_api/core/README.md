# Core Utilities

Shared utilities, middleware, and Django configuration for the backend. This module provides infrastructure-level functionality used across all API applications.

## Purpose

The core module provides Django settings, URL routing, middleware, contract interaction utilities, and ML logging utilities. It does not contain business logic (that's in `api/` apps) or ML models (that's in `ml_service/`).

## Responsibilities

- Django configuration (settings, URLs, middleware)
- Request/response middleware (logging, error handling, security logging)
- Blockchain contract interaction utilities
- ML prediction logging utilities
- Shared serialization helpers

**Does NOT own**:
- Business logic (in `api/` apps)
- ML models (in `ml_service/`)
- Security models (in `security_engine/`)
- Database models (in each app's `models.py`)

## Key Components

### Settings (`core/settings.py`)

**Purpose**: Django configuration, installed apps, middleware, database, REST framework, CORS, logging.

**Key Configurations**:
- `INSTALLED_APPS`: All Django apps and third-party packages
- `MIDDLEWARE`: Request processing pipeline (security, CORS, logging, error handling)
- `DATABASES`: PostgreSQL connection
- `REST_FRAMEWORK`: API configuration (pagination, throttling, authentication)
- `CORS_ALLOWED_ORIGINS`: Allowed frontend origins
- `LOGGING`: Logging configuration (console, file handlers)

**Environment Variables**:
- `SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode (False in production)
- `POSTGRES_*`: Database connection
- `CELERY_BROKER_URL`: Redis URL for Celery
- `WEB3_PROVIDER_HTTP`: Blockchain RPC endpoint
- `CONTRACT_ADDRESS`: Deployed smart contract address

### URL Routing (`core/urls.py`)

**Purpose**: Root URL configuration, API routing, admin, documentation endpoints.

**Routes**:
- `/`: API root endpoint
- `/admin/`: Django admin panel
- `/api/`: API routes (includes all `api/` apps)
- `/swagger/`: Swagger UI documentation
- `/redoc/`: ReDoc documentation
- `/graphql/`: GraphQL playground

**API App Routing**:
- `/api/users/` → `backend_api.api.users.urls`
- `/api/markets/` → `backend_api.api.markets.urls`
- `/api/trades/` → `backend_api.api.trades.urls`
- `/api/ml/` → `backend_api.api.ml_api.urls`
- `/api/admin/` → `security_engine.urls`

### Middleware (`core/utils/middleware.py`)

**Purpose**: Request/response processing, logging, error handling, security event logging.

**Middleware Classes**:

1. **LoggingMiddleware**
   - Logs all requests (method, path, user)
   - Location: `core/utils/middleware.py:LoggingMiddleware`
   - Order: Early in middleware stack

2. **ErrorHandlingMiddleware**
   - Catches unhandled exceptions
   - Returns JSON error responses for API requests
   - Logs exceptions with traceback
   - Location: `core/utils/middleware.py:ErrorHandlingMiddleware`
   - Order: Late in middleware stack (after view execution)

3. **SecurityLoggingMiddleware**
   - Logs security events (rate limit violations, failed logins)
   - Writes to `SecurityLog` model and JSONL files
   - Location: `core/utils/middleware.py:SecurityLoggingMiddleware`
   - Order: After response generation (process_response)

**Middleware Order** (in `settings.py:MIDDLEWARE`):
1. SecurityMiddleware
2. SessionMiddleware
3. CorsMiddleware
4. CommonMiddleware
5. CsrfViewMiddleware
6. AuthenticationMiddleware
7. MessageMiddleware
8. XFrameOptionsMiddleware
9. LoggingMiddleware (custom)
10. ErrorHandlingMiddleware (custom)
11. SecurityLoggingMiddleware (custom)

### Contract Utilities (`core/utils/contracts.py`)

**Purpose**: Web3 contract interaction, event listening, transaction submission.

**Key Classes**:

- `ContractService`: Main service for contract interaction
  - Initializes Web3 connection (HTTP and WebSocket)
  - Loads contract ABI from file
  - Provides sync and async methods for contract calls
  - Handles transaction signing and submission

**Methods**:
- `get_contract_service()`: Singleton factory function
- `ContractService.get_events()`: Listen to contract events
- `ContractService.call_contract()`: Call contract functions
- `ContractService.send_transaction()`: Submit transactions

**Location**: `core/utils/contracts.py`

**Interfaces**:
- Called by: `backend_api/api/indexer/` (for event listening)
- Calls: Web3.py library, blockchain RPC endpoint

### ML Logging Utilities (`core/utils/ml_logger.py`)

**Purpose**: Dual logging for ML predictions (database + file).

**Key Classes**:

- `DualLogger`: Logs ML predictions to both database and file
  - Database: Writes to `ml_service.training.models.TradeRiskPrediction`
  - File: Writes to `backend_api/ml_logs/*.jsonl`

**Methods**:
- `DualLogger.log_risk_event()`: Log trade risk prediction

**Location**: `core/utils/ml_logger.py`

**Interfaces**:
- Called by: `backend_api/api/trades/views.py` (after ML risk assessment)
- Calls: Django ORM, file system

### Serialization Helpers (`core/utils/serializer.py`)

**Purpose**: Standardized API response formatting.

**Functions**:
- `success(data, message)`: Success response wrapper
- `error(message, status_code)`: Error response wrapper

**Location**: `core/utils/serializer.py`

**Usage**: Used by API views for consistent response format.

### Logging Utilities (`core/utils/logging.py`)

**Purpose**: Structured JSON logging for blockchain events.

**Functions**:
- `get_onchain_loggers()`: Returns configured loggers for onchain events
  - `events`: Onchain events (JSONL)
  - `errors`: Indexer errors (JSONL)
  - `duplicates`: Duplicate event suppression (JSONL)

**Location**: `core/utils/logging.py`

**Interfaces**:
- Called by: `backend_api/api/indexer/services/processor.py`

## Execution Flow

### Request Processing

```
1. HTTP Request arrives
2. SecurityMiddleware: Security headers
3. SessionMiddleware: Session handling
4. CorsMiddleware: CORS headers
5. CommonMiddleware: URL normalization
6. CsrfViewMiddleware: CSRF protection
7. AuthenticationMiddleware: User authentication (JWT)
8. MessageMiddleware: Flash messages
9. XFrameOptionsMiddleware: Clickjacking protection
10. LoggingMiddleware: Log request
11. View execution
12. ErrorHandlingMiddleware: Catch exceptions
13. SecurityLoggingMiddleware: Log security events
14. Response returned
```

### ML Prediction Logging

```
1. Trade execution calls ML risk assessment
2. Risk score calculated
3. DualLogger.log_risk_event() called
4. Prediction stored to database (TradeRiskPrediction)
5. Prediction written to file (ml_logs/*.jsonl)
```

### Contract Interaction

```
1. Indexer service calls get_contract_service()
2. ContractService initialized (if not already)
3. Web3 connection established
4. Contract ABI loaded from file
5. Events listened to or transactions submitted
6. Results returned to caller
```

## Interfaces

### Called By

- All API apps: Use settings, middleware, serialization helpers
- `backend_api/api/indexer/`: Uses contract utilities, logging utilities
- `backend_api/api/trades/`: Uses ML logging utilities

### Calls

- Django framework: Settings, middleware, URL routing
- Web3.py: Blockchain interaction
- File system: Log files, contract ABI files
- Django ORM: ML prediction storage

## Security / Constraints

### Trust Boundaries

- Core utilities are infrastructure. They do not enforce business logic security (that's in views).
- Middleware processes all requests. Must be efficient to avoid performance impact.

### Assumptions

- Environment variables are set correctly
- Contract ABI file exists at configured path
- File system is writable for logs
- Database is available for ML prediction storage

### Limits

- Contract service is singleton (not thread-safe for async operations)
- ML logging may fail if database is unavailable (no retry logic)
- Error handling middleware catches all exceptions (may hide bugs)

### Fail-Safe Behavior

- If contract service fails to initialize, it logs warning but does not crash
- If ML logging fails, error is logged but trade execution continues
- If middleware fails, request may return 500 error

## File Structure

```
core/
├── settings.py              # Django settings
├── urls.py                  # URL routing
├── wsgi.py                  # WSGI application
├── asgi.py                  # ASGI application (if used)
├── celery.py                # Celery configuration
├── graphql_schema.py         # GraphQL schema (if used)
└── utils/
    ├── middleware.py        # Custom middleware
    ├── contracts.py         # Contract interaction
    ├── ml_logger.py         # ML logging
    ├── serializer.py        # Response helpers
    ├── logging.py           # Structured logging
    └── abi/                 # Contract ABI files
        └── PredictionMarket.json
```

## Related Documentation

- `backend_api/README.md`: Backend architecture
- `backend_api/api/README.md`: API applications
- `ml_service/README.md`: ML service
- `security_engine/README.md`: Security engine
