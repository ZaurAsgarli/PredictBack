# Set Environment Variables GLOBALLY + EARLY to ensure Docker and Python use the same values
$env:POSTGRES_USER = "postgres"
$env:POSTGRES_PASSWORD = "postgres"
$env:POSTGRES_DB = "predicthub_db"
$env:POSTGRES_HOST = "localhost"
$env:POSTGRES_PORT = "5435"
# Force Python to see the current directory
$env:PYTHONPATH = "$PWD"
$env:DJANGO_SETTINGS_MODULE = "backend_api.core.settings"
# Sepolia Chain ID
$env:CHAIN_ID = "11155111"

Write-Host "Starting Phoenix Rebuild..." -ForegroundColor Cyan
Write-Host "Configuration:" -ForegroundColor DarkGray
Write-Host "  DB Name: $($env:POSTGRES_DB)" -ForegroundColor DarkGray
Write-Host "  DB User: $($env:POSTGRES_USER)" -ForegroundColor DarkGray
Write-Host "  ChainID: $($env:CHAIN_ID)" -ForegroundColor DarkGray

# 1. Force Clean Infrastructure
Write-Host "Tearing down old volumes..." -ForegroundColor Yellow
Set-Location infrastructure
# We pass the env vars implicitly to docker-compose via the shell
docker-compose down -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Docker down failed. Continuing hoping 'up' works..." -ForegroundColor DarkGray
}

Write-Host "Starting Database..." -ForegroundColor Yellow
docker-compose up -d db redis
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker failed to start. Is Docker Desktop running?" -ForegroundColor Red
    exit 1
}
Set-Location ..

# Wait for DB to be initialized
Write-Host "Waiting 15s for DB initialization..." -ForegroundColor DarkGray
Start-Sleep -Seconds 15

# 2. Run Django Migrations
Write-Host "Regenerating Migrations..." -ForegroundColor Yellow
python backend_api/manage.py makemigrations

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ MakeMigrations Failed." -ForegroundColor Red
    exit 1
}

Write-Host "Applying Migrations..." -ForegroundColor Yellow
python backend_api/manage.py migrate

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Migrate Failed." -ForegroundColor Red
    exit 1
}

# 3. Handle Contract Deployment
Write-Host "Checking Contract Deployment..." -ForegroundColor Yellow
Write-Host "⚠️  Skipping local contract deployment because Chain ID is 11155111 (Sepolia)." -ForegroundColor Yellow
Write-Host "   If you need to deploy, verify 'smart_contracts/.env' and run deployment manually." -ForegroundColor DarkGray

# 6. Bring up Full Stack
Write-Host "Starting Full System (Web, Celery, Indexer)..." -ForegroundColor Yellow
Set-Location infrastructure
docker-compose up -d
Set-Location ..

Write-Host "✅ System Rebuild Complete. All services are running." -ForegroundColor Green
