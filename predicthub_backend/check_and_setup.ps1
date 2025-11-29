# PredictHub Backend - Complete Setup Script
# Run this script to check and setup everything from scratch

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "PREDICTHUB BACKEND - SETUP CHECKER" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Step 1: Check Docker
Write-Host "[1/6] Checking Docker..." -ForegroundColor Yellow
try {
    $dockerCheck = docker ps 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Docker is running" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Docker is NOT running!" -ForegroundColor Red
        Write-Host "`n  Please start Docker Desktop first:" -ForegroundColor Yellow
        Write-Host "  1. Open Docker Desktop" -ForegroundColor White
        Write-Host "  2. Wait for it to fully start" -ForegroundColor White
        Write-Host "  3. Run this script again`n" -ForegroundColor White
        exit 1
    }
} catch {
    Write-Host "  ✗ Docker is NOT running!" -ForegroundColor Red
    Write-Host "  Please start Docker Desktop first`n" -ForegroundColor Yellow
    exit 1
}

# Step 2: Check if containers are running
Write-Host "`n[2/6] Checking containers..." -ForegroundColor Yellow
$containers = docker-compose ps 2>&1
if ($containers -match "Up") {
    Write-Host "  ✓ Containers are running" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Containers are not running. Starting them..." -ForegroundColor Yellow
    docker-compose up -d
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Containers started successfully" -ForegroundColor Green
        Write-Host "  ⏳ Waiting 10 seconds for services to initialize..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
    } else {
        Write-Host "  ✗ Failed to start containers" -ForegroundColor Red
        exit 1
    }
}

# Step 3: Check migrations
Write-Host "`n[3/6] Checking migrations..." -ForegroundColor Yellow
$migrations = docker-compose exec -T web python manage.py showmigrations --plan 2>&1
if ($migrations -match "\[ \]") {
    Write-Host "  ⚠ Pending migrations found. Running migrate..." -ForegroundColor Yellow
    docker-compose exec web python manage.py migrate
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Migrations applied" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Migration failed" -ForegroundColor Red
    }
} else {
    Write-Host "  ✓ All migrations are applied" -ForegroundColor Green
}

# Step 4: Check superuser
Write-Host "`n[4/6] Checking superuser account..." -ForegroundColor Yellow
$superuserCheck = docker-compose exec -T web python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); print(User.objects.filter(is_superuser=True).count())" 2>&1
$superuserCount = [int]($superuserCheck | Select-String -Pattern "^\d+$" | ForEach-Object { $_.Matches.Value })
if ($superuserCount -gt 0) {
    Write-Host "  ✓ Superuser account exists ($superuserCount found)" -ForegroundColor Green
    
    # Get superuser details
    $superuserDetails = docker-compose exec -T web python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); su = User.objects.filter(is_superuser=True).first(); print(f'{su.username}|{su.email}')" 2>&1
    if ($superuserDetails -match "\|") {
        $parts = $superuserDetails -split "\|"
        Write-Host "    Username: $($parts[0])" -ForegroundColor Gray
        Write-Host "    Email: $($parts[1])" -ForegroundColor Gray
    }
} else {
    Write-Host "  ✗ No superuser found!" -ForegroundColor Red
    Write-Host "`n  Creating superuser..." -ForegroundColor Yellow
    Write-Host "  (You'll be prompted for username, email, and password)`n" -ForegroundColor White
    docker-compose exec web python manage.py createsuperuser
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Superuser created successfully" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Failed to create superuser" -ForegroundColor Red
    }
}

# Step 5: Check seed data
Write-Host "`n[5/6] Checking seed data..." -ForegroundColor Yellow
$marketCount = docker-compose exec -T web python manage.py shell -c "from markets.models import Market; print(Market.objects.count())" 2>&1 | Select-String -Pattern "^\d+$" | ForEach-Object { [int]$_.Matches.Value }
if ($marketCount -gt 0) {
    Write-Host "  ✓ Seed data exists ($marketCount markets found)" -ForegroundColor Green
} else {
    Write-Host "  ⚠ No seed data found. Running seed command..." -ForegroundColor Yellow
    docker-compose exec web python manage.py seed_data
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Seed data created successfully" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Failed to create seed data" -ForegroundColor Red
    }
}

# Step 6: Final verification
Write-Host "`n[6/6] Final verification..." -ForegroundColor Yellow
Write-Host "`n  Running comprehensive check..." -ForegroundColor Gray
docker-compose exec -T web python manage.py shell < check_setup.py 2>&1 | Select-Object -Last 20

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "SETUP COMPLETE!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Access your application:" -ForegroundColor Yellow
Write-Host "  • Django Admin: http://localhost:8000/admin/" -ForegroundColor White
Write-Host "  • pgAdmin: http://localhost:5050/" -ForegroundColor White
Write-Host "  • API: http://localhost:8000/api/`n" -ForegroundColor White

Write-Host "Quick commands:" -ForegroundColor Yellow
Write-Host "  • View logs: docker-compose logs -f web" -ForegroundColor White
Write-Host "  • Stop: docker-compose down" -ForegroundColor White
Write-Host "  • Restart: docker-compose restart web`n" -ForegroundColor White

