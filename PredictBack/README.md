# PredictHub Backend

Production-ready Django backend for a Community Prediction Market.

[![Django](https://img.shields.io/badge/Django-5.2.8-green.svg)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15.2-red.svg)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

## 🚀 Features

- **User Authentication**: JWT-based authentication with refresh tokens
- **Prediction Markets**: Create and manage prediction markets with YES/NO outcomes
- **AMM Pricing**: Automated Market Maker for dynamic price discovery
- **Trading System**: Buy/sell outcome tokens with real-time price updates
- **Position Tracking**: Track user holdings across all markets
- **Dispute Resolution**: Bond-based dispute system for market resolutions
- **Leaderboards**: Global, weekly, and monthly leaderboards
- **API Documentation**: Swagger/OpenAPI and GraphQL endpoints
- **Async Tasks**: Celery integration for background jobs
- **Webhook Support**: Ready for on-chain indexer integration

## 📦 Tech Stack

- **Django 5.2.8** - Web framework
- **Django REST Framework** - REST API framework
- **Django CORS Headers** - Cross-origin resource sharing
- **Django Environ** - Environment variable management
- **Django REST Framework SimpleJWT** - JWT authentication
- **PostgreSQL** - Database
- **Docker + Docker Compose** - Containerization
- **Celery + Redis** - Asynchronous task queue
- **Swagger/OpenAPI (drf-yasg)** - API documentation
- **GraphQL (Strawberry)** - GraphQL API

## Project Structure

```
predicthub_backend/
├── manage.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── seed.py
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   ├── wsgi.py
│   ├── celery.py
│   └── graphql_schema.py
├── users/
├── markets/
├── trades/
├── positions/
├── disputes/
├── liquidity/
├── analytics/
├── indexer/
└── utils/
```

## 🛠️ Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional, for containerized setup)

### Using Docker (Recommended)

1. **Clone the repository** (if not already done)

2. **Copy environment file**:
```bash
cd predicthub_backend
cp .env.example .env
```

3. **Build and run with Docker Compose**:
```bash
docker-compose up --build
```

This will start:
- PostgreSQL database on port 5432
- Redis on port 6379
- Django web server on port 8000
- Celery worker for async tasks
- Celery beat for scheduled tasks

4. **Run migrations** (in a new terminal or exec into container):
```bash
docker-compose exec web python manage.py migrate
```

5. **Create superuser**:
```bash
docker-compose exec web python manage.py createsuperuser
```

6. **Seed sample data**:
```bash
docker-compose exec web python manage_seed.py
```

### Local Development

1. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Set up PostgreSQL database**:
```bash
# Create database
createdb predicthub_db

# Or using psql:
psql -U postgres
CREATE DATABASE predicthub_db;
```

4. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env with your database and Redis settings
```

5. **Run migrations**:
```bash
python manage.py migrate
```

6. **Create superuser**:
```bash
python manage.py createsuperuser
```

7. **Seed sample data**:
```bash
python manage_seed.py
```

8. **Run development server**:
```bash
python manage.py runserver
```

9. **Run Celery worker** (in separate terminal):
```bash
celery -A config worker -l info
```

10. **Run Celery beat** (in another terminal, for scheduled tasks):
```bash
celery -A config beat -l info
```

## 📡 API Endpoints

### Authentication

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth/signup/` | User registration | No |
| POST | `/auth/login/` | User login | No |
| GET | `/auth/me/` | Get current user profile | Yes |
| POST | `/auth/token/refresh/` | Refresh JWT token | No |

**Example Signup Request**:
```json
POST /auth/signup/
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepassword123",
  "password_confirm": "securepassword123"
}
```

**Example Login Request**:
```json
POST /auth/login/
{
  "email": "john@example.com",
  "password": "securepassword123"
}
```

### Markets

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/markets/` | List all markets (paginated) | No |
| GET | `/markets/featured/` | Get featured markets | No |
| GET | `/markets/{id}/` | Get market details | No |
| GET | `/markets/categories/` | Get all categories | No |
| POST | `/markets/create/` | Create market | Admin |
| POST | `/markets/{id}/resolve/` | Resolve market | Admin |
| GET | `/markets/{id}/trades/` | Get market trades | No |
| GET | `/markets/{id}/position/` | Get user position | Yes |

**Example Create Market** (Admin only):
```json
POST /markets/create/
{
  "title": "Will Bitcoin reach $100k by 2025?",
  "description": "Prediction on Bitcoin price",
  "category": 1,
  "ends_at": "2025-12-31T23:59:59Z"
}
```

### Trades

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/markets/{id}/trade/` | Create a trade (buy/sell) | Yes |
| GET | `/trades/` | List all trades | Yes |
| GET | `/users/me/trades/` | Get user's trades | Yes |

**Example Trade Request**:
```json
POST /markets/1/trade/
{
  "outcome_type": "YES",
  "trade_type": "buy",
  "amount_staked": 100.00
}
```

### Positions

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/users/me/positions/` | Get user's positions | Yes |
| GET | `/markets/{id}/position/` | Get position for specific market | Yes |

### Leaderboard

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/leaderboard/global/` | Global leaderboard | No |
| GET | `/leaderboard/weekly/` | Weekly leaderboard | No |
| GET | `/leaderboard/monthly/` | Monthly leaderboard | No |
| GET | `/leaderboard/user/{id}/` | User leaderboard position | No |

### Webhook

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/webhook/` | Webhook endpoint for on-chain indexer | No |
| GET | `/webhook/rpc/` | RPC endpoint for AMM feeds | No |

## 📚 API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/swagger/
- **ReDoc**: http://localhost:8000/redoc/
- **GraphQL Playground**: http://localhost:8000/graphql/
- **Admin Panel**: http://localhost:8000/admin/

### Using the API

All authenticated endpoints require a JWT token in the Authorization header:
```
Authorization: Bearer <access_token>
```

Example with cURL:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/auth/me/
```

## 🗄️ Database Models

### User
Custom user model extending Django's AbstractUser with prediction market specific fields:
- `total_points`: Accumulated points from winning predictions
- `win_rate`: Percentage of correct predictions
- `streak`: Current winning streak

### Market
Represents a prediction event:
- `title`, `description`: Market details
- `category`: Market category (Sports, Politics, etc.)
- `status`: `active`, `closed`, or `resolved`
- `resolution_outcome`: Final outcome (`YES` or `NO`)
- `liquidity_pool`: Total liquidity in the market
- `fee_percentage`: Trading fee (default 2%)
- `ends_at`: Market end date/time

### OutcomeToken
Each market has 2 outcome tokens (YES/NO):
- `outcome_type`: `YES` or `NO`
- `price`: Current price (0.0 to 1.0)
- `supply`: Total supply of tokens

### Trade
Buy/sell transactions:
- `outcome_type`: `YES` or `NO`
- `trade_type`: `buy` or `sell`
- `amount_staked`: Amount staked in the trade
- `tokens_amount`: Tokens received/paid
- `price_at_execution`: Price when trade was executed

### Position
Tracks user's accumulated holdings per market:
- `yes_tokens`: Number of YES tokens held
- `no_tokens`: Number of NO tokens held
- `total_staked`: Total amount staked

### Resolution
Market resolution details:
- `resolved_outcome`: Final outcome
- `resolver`: Admin who resolved the market
- `dispute_window`: Time window for disputes
- `bond_amount`: Required bond for disputes

### Dispute
User disputes against resolutions:
- `status`: `pending`, `accepted`, or `rejected`
- `bond_amount`: Bond paid for dispute
- `reason`: Dispute reason

### LiquidityEvent
Tracks AMM liquidity changes:
- `event_type`: `add` or `remove`
- `amount`: Liquidity amount

### PriceHistory
Historical price data for charts:
- `yes_price`, `no_price`: Price snapshot
- `timestamp`: When price was recorded

## 💹 AMM Pricing Logic

The Automated Market Maker (AMM) calculates prices dynamically based on liquidity:

```
price_yes = liquidity_yes / (liquidity_yes + liquidity_no)
price_no = liquidity_no / (liquidity_yes + liquidity_no)
```

**How it works**:
- When someone buys YES tokens, YES liquidity increases → YES price goes up
- When someone sells YES tokens, YES liquidity decreases → YES price goes down
- Prices always sum to 1.0 (100%)
- Prices update in real-time with each trade

**Example**:
- Initial: YES = 500, NO = 500 → Prices: YES = 0.5, NO = 0.5
- After buying 100 YES: YES = 600, NO = 500 → Prices: YES = 0.545, NO = 0.455

## 🧪 Testing

Run tests with pytest:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=. --cov-report=html
```

Run specific test file:
```bash
pytest tests/test_models.py
pytest tests/test_api.py
```

## 🚀 Production Deployment

### Checklist

1. **Environment Variables**:
   - Set `DEBUG=False` in `.env`
   - Generate a strong `SECRET_KEY`:
     ```python
     from django.core.management.utils import get_random_secret_key
     print(get_random_secret_key())
     ```
   - Configure proper `ALLOWED_HOSTS`
   - Set secure database credentials
   - Configure CORS origins for your frontend domain

2. **Database**:
   - Use PostgreSQL in production
   - Set up database backups
   - Configure connection pooling

3. **Security**:
   - Set up SSL/TLS certificates
   - Use HTTPS only
   - Configure secure cookie settings
   - Set up rate limiting

4. **Server**:
   - Use a production WSGI server (gunicorn, uwsgi)
   - Set up reverse proxy (nginx, Apache)
   - Configure static file serving
   - Set up process management (supervisor, systemd)

5. **Monitoring**:
   - Set up logging (Sentry, Loggly, etc.)
   - Monitor database performance
   - Set up health checks
   - Monitor Celery tasks

### Example Gunicorn Setup

```bash
pip install gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

### Example Nginx Configuration

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /static/ {
        alias /path/to/staticfiles/;
    }
}
```

## 🐛 Troubleshooting

### Database Connection Issues
- Check PostgreSQL is running: `pg_isready`
- Verify database credentials in `.env`
- Ensure database exists: `psql -l`

### Redis Connection Issues
- Check Redis is running: `redis-cli ping`
- Verify Redis URL in `.env`

### Migration Issues
- Reset migrations: `python manage.py migrate --run-syncdb`
- Check for migration conflicts

### Celery Not Working
- Ensure Redis is running
- Check Celery worker logs
- Verify `CELERY_BROKER_URL` in settings

## 📝 Environment Variables

Key environment variables (see `.env.example`):

- `SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode (True/False)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`: Database settings
- `CELERY_BROKER_URL`: Redis URL for Celery
- `CORS_ALLOWED_ORIGINS`: Frontend origins
- `WEBHOOK_SECRET`: Secret for webhook verification

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

BSD License

## 👥 Support

For issues and questions:
- Check the API documentation at `/swagger/`
- Review the ERD diagram in `erd.md`
- Check Django admin panel at `/admin/`

## 🎯 Roadmap

- [ ] Enhanced AMM with slippage protection
- [ ] Oracle integration for automatic resolution
- [ ] On-chain indexer integration
- [ ] Advanced dispute resolution system
- [ ] Real-time price updates via WebSockets
- [ ] Market creation by users (with approval)
- [ ] Advanced analytics and charts

