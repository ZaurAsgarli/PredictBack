# PredictHub - Decentralized Prediction Market Platform

**SDF2 Build - Production Ready | Dockerized Ecosystem**

A full-stack decentralized prediction market platform integrating Blockchain, Backend, Database, ML, and Security layers in a containerized environment.

[![Django](https://img.shields.io/badge/Django-5.2.8-green.svg)](https://www.djangoproject.com/)
[![Solidity](https://img.shields.io/badge/Solidity-0.8.20-blue.svg)](https://soliditylang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://www.docker.com/)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    BLOCKCHAIN LAYER                         │
│  Smart Contract (PredictionMarket.sol) → Events             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    INDEXER LAYER                            │
│  Event Listener → Processor → Database Sync                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND LAYER (Django)                    │
│  REST API → Business Logic → ORM                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATABASE LAYER                            │
│  PostgreSQL (4NF Normalized) → Materialized Views             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    ML LAYER                                  │
│  Model 1: Trade Risk | Model 3: Token Behavior |            │
│  Model 4: Manipulation | Model 5: Health (MHEWS)             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY LAYER                            │
│  Rate Limiting → Attack Logging → Security Dashboard         │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
PredictBack/
├── smart_contracts/          # Solidity contracts & Hardhat/Brownie
│   ├── contracts/            # PredictionMarket.sol
│   ├── test/                 # Hardhat tests
│   ├── tests/                # Brownie tests (39 tests)
│   ├── scripts/              # Deployment scripts
│   └── build/                # Compiled contracts & ABIs
│
├── predicthub_backend/       # Django backend (Dockerized)
│   ├── config/               # Django settings
│   ├── indexer/              # Blockchain event indexer
│   ├── markets/              # Market management
│   ├── trades/               # Trading system
│   ├── users/                # User management & auth
│   ├── ml/                   # Machine Learning models
│   │   ├── models/           # Trained models (.pkl)
│   │   ├── notebooks/        # Jupyter notebooks
│   │   ├── services/         # ML service layer
│   │   └── model_loader.py   # Model loading utilities
│   ├── ml_api/               # ML API endpoints
│   ├── security/             # Security logging & monitoring
│   ├── tests/                # Test suite
│   │   └── master_integration_suite.py  # Master E2E tests
│   ├── Dockerfile            # Docker image definition
│   ├── docker-compose.yml    # Docker Compose configuration
│   └── requirements.txt      # Python dependencies
│
├── README.md                 # This file
└── TESTING_GUIDE.md          # Comprehensive testing guide
```

---

## 🚀 Quick Start (Docker)

### Prerequisites

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **Node.js** 18+ (for smart contract deployment)

### 1. Clone Repository

```bash
git clone <repository-url>
cd PredictBack
```

### 2. Deploy Smart Contract

```bash
cd smart_contracts
npm install
npx hardhat run scripts/deploy_and_export.js --network localhost
```

**Note:** Update `predicthub_backend/.env` with the deployed contract address.

### 3. Start Docker Services

```bash
cd predicthub_backend
docker-compose up -d
```

This starts:
- **web**: Django server (port 8000)
- **db**: PostgreSQL (port 5432)
- **redis**: Redis (port 6379)
- **celery**: Celery worker
- **celery-beat**: Celery scheduler
- **indexer**: Event listener service

### 4. Run Migrations

```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py seed_knowledge_tags
```

### 5. Verify System

```bash
# Run master integration test suite
docker-compose exec web python tests/master_integration_suite.py
```

**Expected Output:**
```
✅ DB Connection: PASS
✅ Migrations: PASS
✅ Required Tables: PASS
✅ Event Payload Parsing: PASS
✅ Signup API: PASS
✅ Database Verification: PASS
✅ Rate Limit Test: PASS
✅ SQL Injection Protection: PASS
✅ Audit Log Check: PASS
✅ Model 1: Trade Risk: PASS
✅ ML API Endpoint: PASS
```

---

## 🧪 Testing

### Master Integration Test Suite

The comprehensive test suite verifies all layers:

```bash
# Run inside Docker container
docker-compose exec web python tests/master_integration_suite.py
```

**What it tests:**
1. ✅ Database connection & migrations
2. ✅ Smart contract event processing (mock)
3. ✅ API endpoints & data flow
4. ✅ Security (rate limiting, SQL injection, audit logs)
5. ✅ ML model inference

**See [`TESTING_GUIDE.md`](TESTING_GUIDE.md) for detailed manual testing procedures.**

### Unit Tests

```bash
# Smart Contract Tests
cd smart_contracts
brownie test

# Backend Tests
cd predicthub_backend
docker-compose exec web pytest
```

---

## 🔧 Tech Stack

### Backend
- **Framework**: Django 5.2.8 + Django REST Framework
- **Database**: PostgreSQL 15 (4NF normalized)
- **Cache/Queue**: Redis 7
- **Task Queue**: Celery 5.4
- **Authentication**: JWT (djangorestframework-simplejwt)

### Blockchain
- **Language**: Solidity 0.8.20
- **Testing**: Hardhat + Brownie
- **Web3**: web3.py 7.14

### Machine Learning
- **Models**: Isolation Forest, XGBoost, Random Forest
- **Libraries**: scikit-learn, pandas, numpy, joblib
- **Notebooks**: Jupyter

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **API Docs**: Swagger/OpenAPI (drf-yasg)
- **GraphQL**: Strawberry Django

---

## 📊 Key Features

- ✅ **Smart Contract Events**: All actions emit events
- ✅ **Event Indexing**: Automatic blockchain → database sync
- ✅ **4NF Database**: Normalized schema with materialized views
- ✅ **ML Integration**: 5 models with database storage
- ✅ **Security Layer**: Rate limiting, attack logging, security dashboard
- ✅ **Comprehensive Tests**: 39 Brownie tests + Django tests + Integration suite
- ✅ **API Documentation**: Swagger/OpenAPI + GraphQL
- ✅ **RPC Server**: JSON-RPC 2.0 for admin tools

---

## 🔗 API Endpoints

### Core Endpoints

- `GET /api/markets/` - List markets
- `POST /api/markets/{id}/trade/` - Place trade
- `GET /api/trades/` - List trades
- `GET /api/indexer/rpc/` - JSON-RPC endpoint

### ML Endpoints

- `POST /api/ml/risk/predict/` - Predict trade risk (Model 1)
- `GET /api/ml/token-behavior/market/{id}/` - Token behavior forecast (Model 3)
- `GET /api/ml/health/` - Platform health status (Model 5)
- `GET /api/ml/manipulation/market/{id}/` - Manipulation analysis (Model 4)

### Security Endpoints

- `GET /api/admin/security-logs/` - Security logs dashboard
- `GET /api/admin/logs/` - Filtered security logs
- `GET /api/admin/logs/stats/` - Security statistics

### Documentation

- `GET /swagger/` - Swagger UI
- `GET /redoc/` - ReDoc
- `GET /graphql/` - GraphQL Playground

---

## 🔒 Security Features

- **Rate Limiting**: 100 req/hour (anonymous), 1000 req/hour (authenticated)
- **Attack Logging**: Automatic logging of rate limit violations and failed logins
- **Security Dashboard**: Real-time security event monitoring via REST API
- **SQL Injection Protection**: Django ORM prevents SQL injection
- **Audit Trail**: All security events logged to `security_logs` table

**View Security Logs:**
- API: `http://localhost:8000/api/admin/security-logs/`
- Admin Panel: `http://localhost:8000/admin/security/securitylog/`

---

## 🐳 Docker Services

### Services Overview

| Service | Port | Description |
|---------|------|-------------|
| web | 8000 | Django REST API server |
| db | 5432 | PostgreSQL database |
| redis | 6379 | Redis cache & message broker |
| celery | - | Celery worker for async tasks |
| celery-beat | - | Celery scheduler |
| indexer | - | Blockchain event listener |

### Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f web
docker-compose logs -f indexer

# Execute commands in container
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py shell

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

---

## 📚 Documentation

- **Root**: This file (architecture & quick start)
- **Backend**: [`predicthub_backend/README.md`](predicthub_backend/README.md)
- **Contracts**: [`smart_contracts/README.md`](smart_contracts/README.md)
- **Database**: [`predicthub_backend/db_docs/README.md`](predicthub_backend/db_docs/README.md)
- **ML**: [`predicthub_backend/ml/README.md`](predicthub_backend/ml/README.md)
- **Testing**: [`TESTING_GUIDE.md`](TESTING_GUIDE.md)

---

## 🔧 Environment Variables

Create `predicthub_backend/.env`:

```bash
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
POSTGRES_DB=predicthub_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis
CELERY_BROKER_URL=redis://redis:6379/0

# Blockchain
WEB3_PROVIDER_URL=http://host.docker.internal:8545
CONTRACT_ADDRESS=0x...  # From smart contract deployment
```

---

## 🧪 Running Tests

### Master Integration Suite

```bash
# Run comprehensive E2E tests
docker-compose exec web python tests/master_integration_suite.py
```

### Unit Tests

```bash
# Smart Contract Tests
cd smart_contracts
brownie test

# Backend Tests
cd predicthub_backend
docker-compose exec web pytest
```

### Security Tests

```bash
# Test security logging system
docker-compose exec web python tests/demo_security.py
```

**See [`TESTING_GUIDE.md`](TESTING_GUIDE.md) for complete testing procedures.**

---

## 📈 Monitoring

### Indexer Status

```bash
# Via JSON-RPC
curl -X POST http://localhost:8000/api/indexer/rpc/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"get_indexer_status","params":{},"id":1}'
```

### Security Monitoring

```bash
# View security logs
curl http://localhost:8000/api/admin/security-logs/

# Get statistics
curl http://localhost:8000/api/admin/logs/stats/
```

### Database Queries

```sql
-- Check indexed events
SELECT COUNT(*) FROM indexer_onchaineventlog;

-- Check ML predictions
SELECT COUNT(*) FROM ml_traderiskprediction;

-- Check security logs
SELECT event_type, COUNT(*) FROM security_logs GROUP BY event_type;
```

---

## 🛠️ Development

### Adding New Events

1. Add event to `smart_contracts/contracts/PredictionMarket.sol`
2. Update `EventProcessor` in `predicthub_backend/indexer/services/processor.py`
3. Add test in `smart_contracts/tests/`
4. Run migrations if new DB fields needed

### Adding New ML Models

1. Create model file in `predicthub_backend/ml/`
2. Add service in `predicthub_backend/ml/services/`
3. Create API endpoint in `predicthub_backend/ml_api/views.py`
4. Add DB model in `predicthub_backend/ml/models.py` (if using Django models)
5. Run migrations

---

## ✅ SDF2 Requirements Status

- ✅ Smart Contract with events (`UserCreated`, `LiquidityAdded`, `TransactionCreated`)
- ✅ ≥10 Brownie tests (39 tests total)
- ✅ 4NF Database schema
- ✅ Materialized view for dashboard
- ✅ Indexer with event listener
- ✅ API endpoints (`/api/history`, `/api/user/{id}`)
- ✅ JSON-RPC server
- ✅ ML models with DB integration
- ✅ Docker Compose setup
- ✅ Security Layer (rate limiting, attack logging, security dashboard)
- ✅ **Master Integration Test Suite** (E2E testing)

**All requirements met!** 🎉

---

## 📝 License

BSD License

---

## 🤝 Support

- **API Docs**: http://localhost:8000/swagger/
- **Admin Panel**: http://localhost:8000/admin/
- **Testing Guide**: See `TESTING_GUIDE.md`
- **Integration Tests**: `docker-compose exec web python tests/master_integration_suite.py`

---

## 🎯 Quick Reference

### Key Commands

```bash
# Start services
cd predicthub_backend
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Run integration tests
docker-compose exec web python tests/master_integration_suite.py

# View logs
docker-compose logs -f web
```

### Key URLs

- API Root: http://localhost:8000/
- Swagger: http://localhost:8000/swagger/
- Admin: http://localhost:8000/admin/
- GraphQL: http://localhost:8000/graphql/
- Security Logs: http://localhost:8000/api/admin/security-logs/

---

**End of README** ✅
