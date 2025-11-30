"""
Django management command to verify ML model database integration.

This command:
1. Tests that predictions can be saved to database
2. Verifies data can be retrieved
3. Checks model integration points
4. Generates a verification report
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from ml.models import (
    TradeRiskPrediction,
    MarketManipulationScore,
    PlatformHealthMetric,
    ModelPredictionAudit,
)
from ml.services.db_storage_service import (
    save_trade_risk_prediction,
    save_manipulation_score,
    save_platform_health_metric,
    get_recent_predictions,
    get_prediction_statistics,
)
from ml.model_loader import predict_trade_risk
from ml.features import build_features
from ml.notebooks.model_4_manipulation import detect_market_manipulation, generate_synthetic_manipulation_data
from ml.notebooks.model_5_mhews import calculate_market_health, generate_synthetic_model_outputs
import pandas as pd


class Command(BaseCommand):
    help = 'Verify ML model database integration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-all',
            action='store_true',
            help='Run all integration tests',
        )
        parser.add_argument(
            '--test-model1',
            action='store_true',
            help='Test Model 1 (Trade Risk) integration',
        )
        parser.add_argument(
            '--test-model4',
            action='store_true',
            help='Test Model 4 (Manipulation) integration',
        )
        parser.add_argument(
            '--test-model5',
            action='store_true',
            help='Test Model 5 (Health) integration',
        )
        parser.add_argument(
            '--verify-storage',
            action='store_true',
            help='Verify predictions are stored in database',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS('ML Model Database Integration Verification'))
        self.stdout.write(self.style.SUCCESS('='*60))
        
        all_tests = options['test_all'] or not any([
            options['test_model1'],
            options['test_model4'],
            options['test_model5'],
            options['verify_storage'],
        ])
        
        if all_tests or options['test_model1']:
            self.test_model1_integration()
        
        if all_tests or options['test_model4']:
            self.test_model4_integration()
        
        if all_tests or options['test_model5']:
            self.test_model5_integration()
        
        if all_tests or options['verify_storage']:
            self.verify_storage()
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('Verification Complete!'))
        self.stdout.write(self.style.SUCCESS('='*60))

    def test_model1_integration(self):
        """Test Model 1 (Trade Risk) database integration"""
        self.stdout.write('\n[TEST] Model 1: Trade Risk Prediction Integration')
        self.stdout.write('-' * 60)
        
        try:
            # Create test data
            test_data = pd.DataFrame([{
                'user_id': 1,
                'created_at': timezone.now(),
                'amount_staked': 100.0,
            }])
            
            # Build features
            features = build_features(test_data)
            
            # Get prediction
            result = predict_trade_risk(features)
            
            # Save to database
            prediction = save_trade_risk_prediction(
                user_id=1,
                trade_id=None,
                market_id=None,
                score=result['score'],
                label=result['label'],
                risk_level=result['risk_level'],
                features={'amount_staked': 100.0},
            )
            
            # Verify saved
            saved = TradeRiskPrediction.objects.get(id=prediction.id)
            assert saved.score == result['score']
            assert saved.label == result['label']
            assert saved.risk_level == result['risk_level']
            
            self.stdout.write(self.style.SUCCESS('✅ Model 1: Prediction saved to database'))
            self.stdout.write(f'   Prediction ID: {saved.id}')
            self.stdout.write(f'   Score: {saved.score:.3f}')
            self.stdout.write(f'   Risk Level: {saved.risk_level}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Model 1: FAILED - {e}'))
            import traceback
            traceback.print_exc()

    def test_model4_integration(self):
        """Test Model 4 (Market Manipulation) database integration"""
        self.stdout.write('\n[TEST] Model 4: Market Manipulation Integration')
        self.stdout.write('-' * 60)
        
        try:
            # Generate synthetic data
            df_trades = generate_synthetic_manipulation_data(n_markets=2, n_users=10)
            
            # Run detection
            results = detect_market_manipulation(df_trades, market_id=1)
            
            if not results.empty:
                # Save first result to database
                row = results.iloc[0]
                score = save_manipulation_score(
                    market_id=int(row['market_id']),
                    user_id=int(row['user_id']),
                    manipulation_score=float(row['manipulation_score']),
                    is_manipulation_suspected=bool(row['is_manipulation_suspected']),
                    risk_level=str(row['risk_level']),
                    pump_dump_score=float(row['pump_dump_score']),
                    wash_trading_score=float(row['wash_trading_score']),
                )
                
                # Verify saved
                saved = MarketManipulationScore.objects.get(id=score.id)
                assert saved.manipulation_score == float(row['manipulation_score'])
                
                self.stdout.write(self.style.SUCCESS('✅ Model 4: Prediction saved to database'))
                self.stdout.write(f'   Score ID: {saved.id}')
                self.stdout.write(f'   Market ID: {saved.market_id}')
                self.stdout.write(f'   Manipulation Score: {saved.manipulation_score:.3f}')
                self.stdout.write(f'   Risk Level: {saved.risk_level}')
            else:
                self.stdout.write(self.style.WARNING('⚠️  Model 4: No results to save (expected with synthetic data)'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Model 4: FAILED - {e}'))
            import traceback
            traceback.print_exc()

    def test_model5_integration(self):
        """Test Model 5 (Platform Health) database integration"""
        self.stdout.write('\n[TEST] Model 5: Platform Health Integration')
        self.stdout.write('-' * 60)
        
        try:
            # Generate synthetic model outputs
            df_m1, df_m2, df_m3, df_m4 = generate_synthetic_model_outputs()
            
            # Calculate health
            health_df = calculate_market_health(
                df_model1=df_m1,
                df_model2=df_m2,
                df_model3=df_m3,
                df_model4=df_m4,
            )
            
            if not health_df.empty:
                row = health_df.iloc[0]
                
                # Save to database
                metric = save_platform_health_metric(
                    platform_stress_level=float(row['platform_stress_level']),
                    systemic_risk_index=float(row['systemic_risk_index']),
                    health_status=str(row['health_status']),
                    alert_level=str(row['alert_level']),
                    model1_stress_score=float(row['model1_stress_score']),
                    model2_stress_score=float(row['model2_stress_score']),
                    model3_stress_score=float(row['model3_stress_score']),
                    model4_stress_score=float(row['model4_stress_score']),
                    alert_messages=str(row['alert_messages']),
                )
                
                # Verify saved
                saved = PlatformHealthMetric.objects.get(id=metric.id)
                assert saved.platform_stress_level == float(row['platform_stress_level'])
                
                self.stdout.write(self.style.SUCCESS('✅ Model 5: Prediction saved to database'))
                self.stdout.write(f'   Metric ID: {saved.id}')
                self.stdout.write(f'   Platform Stress: {saved.platform_stress_level:.2%}')
                self.stdout.write(f'   Health Status: {saved.health_status}')
                self.stdout.write(f'   Alert Level: {saved.alert_level}')
            else:
                self.stdout.write(self.style.WARNING('⚠️  Model 5: No results to save'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Model 5: FAILED - {e}'))
            import traceback
            traceback.print_exc()

    def verify_storage(self):
        """Verify predictions are stored and retrievable"""
        self.stdout.write('\n[VERIFY] Database Storage Verification')
        self.stdout.write('-' * 60)
        
        # Check Model 1 predictions
        model1_count = TradeRiskPrediction.objects.count()
        self.stdout.write(f'Model 1 Predictions: {model1_count}')
        
        if model1_count > 0:
            latest = TradeRiskPrediction.objects.latest('created_at')
            self.stdout.write(f'  Latest: ID {latest.id}, Score: {latest.score:.3f}, Risk: {latest.risk_level}')
        
        # Check Model 4 predictions
        model4_count = MarketManipulationScore.objects.count()
        self.stdout.write(f'Model 4 Predictions: {model4_count}')
        
        if model4_count > 0:
            latest = MarketManipulationScore.objects.latest('created_at')
            self.stdout.write(f'  Latest: ID {latest.id}, Score: {latest.manipulation_score:.3f}, Risk: {latest.risk_level}')
        
        # Check Model 5 predictions
        model5_count = PlatformHealthMetric.objects.count()
        self.stdout.write(f'Model 5 Predictions: {model5_count}')
        
        if model5_count > 0:
            latest = PlatformHealthMetric.objects.latest('created_at')
            self.stdout.write(f'  Latest: ID {latest.id}, Stress: {latest.platform_stress_level:.2%}, Status: {latest.health_status}')
        
        # Check audit logs
        audit_count = ModelPredictionAudit.objects.count()
        self.stdout.write(f'Audit Logs: {audit_count}')
        
        # Get statistics
        stats = get_prediction_statistics(days=7)
        self.stdout.write(f'\nStatistics (last 7 days):')
        self.stdout.write(f'  Total Predictions: {stats["total_predictions"]}')
        self.stdout.write(f'  Successful: {stats["successful_predictions"]}')
        self.stdout.write(f'  Failed: {stats["failed_predictions"]}')
        self.stdout.write(f'  Success Rate: {stats["success_rate"]:.2%}')
        
        if model1_count > 0 or model4_count > 0 or model5_count > 0:
            self.stdout.write(self.style.SUCCESS('\n✅ Database integration verified - predictions are being stored!'))
        else:
            self.stdout.write(self.style.WARNING('\n⚠️  No predictions found in database. Run tests to generate data.'))

