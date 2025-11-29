# PredictHub Backend - Complete Setup Checklist

## Prerequisites

### 1. Docker Desktop
- [ ] Docker Desktop is installed
- [ ] Docker Desktop is running (green icon in system tray)
- [ ] Verify: `docker ps` should work (not show errors)

### 2. Environment Variables
- [ ] `.env` file exists in `predicthub_backend/` directory
- [ ] Contains required variables (see `.env.example`)

## Step-by-Step Setup

### Step 1: Start Docker Containers
```bash
cd C:\Users\HP\Desktop\First-Django-backend\predicthub_backend
docker-compose up -d
```

**Expected output:**
- All services start (db, pgadmin, redis, web, celery, celery-beat)
- No errors

**Verify:**
```bash
docker-compose ps
```
All services should show "Up" status.

### Step 2: Run Migrations
```bash
docker-compose exec web python manage.py migrate
```

**Expected output:**
- All migrations applied successfully
- No errors

### Step 3: Create Superuser (if not exists)
```bash
docker-compose exec web python manage.py createsuperuser
```

**Enter:**
- Username: (your choice)
- Email: (your email)
- Password: (your password)

**OR check if superuser exists:**
```bash
docker-compose exec web python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); print('Superusers:', User.objects.filter(is_superuser=True).count())"
```

### Step 4: Seed Example Data
```bash
docker-compose exec web python manage.py seed_data
```

**Expected output:**
- Categories created
- Users created
- Markets created
- Trades, positions, etc. created
- Summary with counts

### Step 5: Verify Everything
```bash
docker-compose exec web python manage.py shell < check_setup.py
```

**OR manually check:**
```bash
docker-compose exec web python manage.py shell
```

Then in Python shell:
```python
from django.contrib.auth import get_user_model
User = get_user_model()
print("Superusers:", User.objects.filter(is_superuser=True).count())
from markets.models import Market
print("Markets:", Market.objects.count())
exit()
```

## Access Points

Once everything is running:

1. **Django Admin Panel**
   - URL: http://localhost:8000/admin/
   - Login with superuser credentials

2. **pgAdmin (Database Management)**
   - URL: http://localhost:5050/
   - Email: `admin@gmail.com` (or from `.env`)
   - Password: `admin` (or from `.env`)
   - Add server:
     - Host: `db`
     - Port: `5432`
     - Database: `predicthub_db`
     - Username: `postgres`
     - Password: `postgres`

3. **Django API**
   - URL: http://localhost:8000/api/
   - Check API documentation at: http://localhost:8000/swagger/

## Troubleshooting

### Docker not running
**Error:** `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`

**Solution:**
1. Open Docker Desktop application
2. Wait for it to fully start (green icon)
3. Try again

### Containers won't start
**Check logs:**
```bash
docker-compose logs
```

**Restart containers:**
```bash
docker-compose down
docker-compose up -d
```

### Database connection errors
**Check if database is healthy:**
```bash
docker-compose ps db
```

**Check database logs:**
```bash
docker-compose logs db
```

### No superuser
**Create one:**
```bash
docker-compose exec web python manage.py createsuperuser
```

### No seed data
**Run seed command:**
```bash
docker-compose exec web python manage.py seed_data
```

**To clear and reseed:**
```bash
docker-compose exec web python manage.py seed_data --clear
```

## Quick Commands Reference

```bash
# Start everything
docker-compose up -d

# Stop everything
docker-compose down

# View logs
docker-compose logs -f web

# Run Django commands
docker-compose exec web python manage.py <command>

# Access Django shell
docker-compose exec web python manage.py shell

# Check container status
docker-compose ps

# Restart a service
docker-compose restart web
```

## Verification Checklist

After setup, verify:

- [ ] Docker containers are running (`docker-compose ps`)
- [ ] Migrations are applied (`docker-compose exec web python manage.py showmigrations`)
- [ ] Superuser exists (check in admin panel or shell)
- [ ] Seed data is loaded (check admin panel)
- [ ] Admin panel accessible (http://localhost:8000/admin/)
- [ ] pgAdmin accessible (http://localhost:5050/)
- [ ] Database connection works (check setup script)

## Next Steps

1. Access admin panel and browse seeded data
2. Test API endpoints
3. Configure pgAdmin to view database
4. Start developing!

