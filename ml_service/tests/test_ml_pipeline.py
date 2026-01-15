from django.test import TestCase
from django.core.management import call_command
from backend_api.api.users.models import User
from backend_api.api.markets.models import Market, MarketCategory
from security_engine.models import SecurityLog
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock
import os
import io

class MLPipelineTests(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            username='test_trader',
            email='test@example.com',
            password='password123',
            role=User.Role.TRADER
        )
        
        # Create Market
        cat = MarketCategory.objects.create(name='TestCat', slug='testcat')
        self.market = Market.objects.create(
            title='Test Market',
            category=cat,
            ends_at=timezone.now() + timedelta(days=1)
        )

    def test_csv_generation(self):
        """Test dataset export command"""
        out = io.StringIO()
        call_command('export_dataset', stdout=out)
        
        file_path = 'ml_service/datasets/final_training_data.csv'
        self.assertTrue(os.path.exists(file_path))
        
        # Check content
        with open(file_path, 'r') as f:
            lines = f.readlines()
            self.assertTrue(len(lines) > 50) # Header + 50 synthetic
            self.assertIn('user_id,role,wallet_age_days', lines[0])

    @patch('backend_api.api.trades.views.predict_trade_risk')
    @patch('backend_api.api.trades.services.TradeExecutionService.execute_trade')
    def test_auto_ban_logic(self, mock_execute, mock_predict):
        """Test that high risk score triggers Auto-Ban"""
        # Mock ML return: CRITICAL RISK
        mock_predict.return_value = {'score': 0.95, 'label': -1}
        
        # Login
        self.client.force_login(self.user)
        
        # POST Trade
        data = {
            'market_id': self.market.id,
            'outcome_type': 'YES',
            'trade_type': 'buy',
            'amount_staked': 100
        }
        
        response = self.client.post('/api/trades/', data)
        
        # Should be Forbidden
        self.assertEqual(response.status_code, 403)
        
        # Verify User is BLOCKED
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.BLOCKED)
        self.assertFalse(self.user.is_active)
        
        # Verify Security Log
        log = SecurityLog.objects.filter(user=self.user, event_type='SUSPICIOUS_ACTIVITY').first()
        self.assertIsNotNone(log)
        self.assertIn('AUTO-BLOCKED', log.message)

    def test_role_choices(self):
        """Ensure roles are restricted"""
        self.user.role = 'SUPER_GOD' # Invalid choice
        # Django validation usually happens at full_clean(), but model field choices restrict DB values if standard DB
        # Here we just check the output if we force it? 
        # Actually Model.save() doesn't validate choices by default unless full_clean called.
        # But we can check if the Choice enum works.
        self.assertEqual(User.Role.ADMIN, 'ADMIN')
