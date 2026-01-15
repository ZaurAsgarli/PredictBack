from django.core.management.base import BaseCommand
from backend_api.api.users.models import User
from backend_api.api.trades.models import Trade
from django.db.models import Count, Avg, Sum
from django.utils import timezone
import csv
import os
import random

class Command(BaseCommand):
    help = 'Exports final training dataset for ML Service'

    def handle(self, *args, **options):
        self.stdout.write("Generating Final Training Dataset...")
        
        # Output path
        output_dir = 'ml_service/datasets'
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, 'final_training_data.csv')
        
        # Open CSV
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            # Header
            writer.writerow(['user_id', 'role', 'wallet_age_days', 'total_trades', 'avg_trade_value', 'failed_login_count', 'risk_score', 'label'])
            
            # Fetch Users with aggregated trade data
            users = User.objects.annotate(
                trade_count=Count('trades'),
                avg_value=Avg('trades__amount_staked')
            )
            
            count = 0
            for u in users:
                # Calculate aggregated features
                wallet_age = (timezone.now() - u.created_at).days
                total_trades = u.trade_count
                avg_val = float(u.avg_value or 0)
                
                # Heuristic Risk Score (Mocking what the ML model sees)
                # If BLOCKED, risk is 0.95, else low
                risk_score = 0.95 if u.role == 'BLOCKED' else 0.10
                
                # Label: 1 (Bad) if Blocked, 0 (Good) otherwise
                label = 1 if u.role == 'BLOCKED' else 0
                
                writer.writerow([
                    u.id, 
                    u.role, 
                    wallet_age, 
                    total_trades, 
                    avg_val, 
                    0, # failed_login_count (placeholder)
                    risk_score,
                    label
                ])
                count += 1
                
            self.stdout.write(self.style.SUCCESS(f"Exported {count} real rows."))
            
            # Synthetic Injection for Robustness (User Request)
            # Inject 50 "BLOCKED" users to ensure dataset has examples
            for i in range(50):
                writer.writerow([
                    999900 + i, # Fake ID
                    'BLOCKED',
                    random.randint(1, 30), # New account
                    random.randint(50, 200), # High velocity
                    random.uniform(5000, 10000), # High value
                    random.randint(3, 10), # Failed logins
                    0.99, # High Score
                    1 # HUD Label
                ])
                
            self.stdout.write(self.style.SUCCESS("Injected 50 synthetic high-risk rows."))
            self.stdout.write(self.style.SUCCESS(f"Saved to {file_path}"))
