#!/bin/bash
set -e

echo "🔥 Starting Phoenix Rebuild..."

# Navigate to backend_api
cd backend_api

echo "🛠️  Regenerating Migrations..."
python manage.py makemigrations api_disputes api_indexer api_liquidity api_markets api_positions api_trades api_users ml_service_training security_engine

echo "💾 Applying Migrations..."
python manage.py migrate

# Return to root
cd ..

echo "⛓️  Deploying Smart Contract..."
cd smart_contracts
# Assuming deploy.js exists and handles deployment + saving address
# You might need to adjust the command based on your actual hardhat/truffle setup
# Example: npx hardhat run scripts/deploy.js --network localhost
if [ -f "scripts/deploy.js" ]; then
    npx hardhat run scripts/deploy.js --network localhost
else
    echo "⚠️  scripts/deploy.js not found. Skipping contract deployment."
fi

echo "✅ System Rebuild Complete."
