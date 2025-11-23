# Seed Data Guide

This guide explains how to populate the database with example data for all models.

## Quick Start

### Using Docker (Recommended)

1. **Make sure your containers are running:**
   ```bash
   docker-compose up -d
   ```

2. **Run the seed command:**
   ```bash
   docker-compose exec web python manage.py seed_data
   ```

3. **To clear existing data and reseed:**
   ```bash
   docker-compose exec web python manage.py seed_data --clear
   ```

### Using Local Python

1. **Activate your virtual environment:**
   ```bash
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

2. **Run the seed command:**
   ```bash
   python manage.py seed_data
   ```

## What Gets Created

The seed command creates example data for all models:

### 1. Market Categories (4 examples)
- Sports
- Politics
- Technology
- Entertainment

### 2. Users (4 examples)
- alice_trader (alice@example.com) - 1250.50 points, 68.5% win rate
- bob_predictor (bob@example.com) - 890.25 points, 55.2% win rate
- charlie_market (charlie@example.com) - 2100.75 points, 72.8% win rate
- diana_admin (diana@example.com) - 500.00 points, 45.0% win rate

**Default password for all users:** `password123`

### 3. Markets (4 examples)
- "Will the Lakers win the NBA Championship in 2024?" (Sports, Active)
- "Will Bitcoin reach $100,000 by end of 2024?" (Technology, Active)
- "Will the new Marvel movie gross over $500M worldwide?" (Entertainment, Active)
- "Will there be a major policy change announced before Q2 2024?" (Politics, Resolved)

### 4. Outcome Tokens
- YES and NO tokens for each market with initial 50/50 pricing

### 5. Trades (4 examples)
- Various buy/sell trades across different markets and users

### 6. Positions (4 examples)
- User positions tracking their token holdings per market

### 7. Liquidity Events (4 examples)
- Add and remove liquidity events for different markets

### 8. Disputes (2 examples)
- Pending and accepted disputes on resolved markets

### 9. Resolutions (1 example)
- Resolution for the politics market (YES outcome)

### 10. Price History
- Historical price data for chart visualization (5 entries per market)

### 11. Onchain Transactions (3 examples)
- SUCCESS and PENDING transaction records

### 12. Onchain Event Logs (3 examples)
- MarketCreated, TradeExecuted, and LiquidityAdded event logs

## Viewing Data in Admin Panel

After seeding, you can view all data in the Django admin panel:

1. **Access admin panel:**
   ```
   http://localhost:8000/admin/
   ```

2. **Login with superuser credentials:**
   - If you haven't created a superuser yet:
     ```bash
     docker-compose exec web python manage.py createsuperuser
     ```

3. **Browse all models:**
   - Users
   - Market Categories
   - Markets
   - Outcome Tokens
   - Trades
   - Positions
   - Liquidity Events
   - Disputes
   - Resolutions
   - Price History
   - Onchain Transactions
   - Onchain Event Logs

## Command Options

```bash
# Basic seed (skips existing data)
python manage.py seed_data

# Clear all data and reseed
python manage.py seed_data --clear
```

## Notes

- The seed command uses `get_or_create()` for most models, so running it multiple times won't create duplicates
- Use `--clear` flag to remove existing data before seeding
- All generated transaction hashes and addresses are random and not real blockchain data
- User passwords are set to `password123` for testing purposes

## Troubleshooting

**Issue:** Command not found
- **Solution:** Make sure you're running from the `predicthub_backend` directory and Django is installed

**Issue:** Database errors
- **Solution:** Ensure migrations are applied: `python manage.py migrate`

**Issue:** Permission errors
- **Solution:** Make sure your database user has proper permissions

