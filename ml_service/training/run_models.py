"""
Helper script to run Models 4 and 5 with proper Python path handling.

Usage:
    python run_models.py --model 4    # Run Model 4
    python run_models.py --model 5    # Run Model 5
    python run_models.py --all       # Run both models
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def run_model_4():
    """Run Model 4: Market Manipulation Detection"""
    print("="*60)
    print("Running Model 4: Market Manipulation Pattern Classifier")
    print("="*60)
    try:
        from ml_service.training.notebooks.model_4_manipulation import (
            generate_synthetic_manipulation_data,
            detect_market_manipulation
        )
        
        print("\nGenerating synthetic trade data...")
        df_trades = generate_synthetic_manipulation_data()
        print(f"Generated {len(df_trades)} trades")
        
        print("\nDetecting market manipulation patterns...")
        results = detect_market_manipulation(df_trades)
        
        print(f"\nDetected {results['is_manipulation_suspected'].sum()} suspicious cases")
        print("\nTop manipulation scores:")
        print(results.nlargest(10, 'manipulation_score')[['market_id', 'user_id', 'manipulation_score', 'risk_level']])
        
        print("\nRisk level distribution:")
        print(results['risk_level'].value_counts())
        print("\n" + "="*60)
        print("Model 4 completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"Error running Model 4: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_model_5():
    """Run Model 5: Market Health Early Warning System"""
    print("="*60)
    print("Running Model 5: Market Health Early Warning System (MHEWS)")
    print("="*60)
    try:
        from ml_service.training.notebooks.model_5_mhews import (
            generate_synthetic_model_outputs,
            calculate_market_health
        )
        
        print("\nGenerating synthetic model outputs...")
        df_m1, df_m2, df_m3, df_m4 = generate_synthetic_model_outputs()
        
        print("\nCalculating Market Health Early Warning System metrics...")
        health_df = calculate_market_health(
            df_model1=df_m1,
            df_model2=df_m2,
            df_model3=df_m3,
            df_model4=df_m4,
        )
        
        print("\n" + "="*60)
        print("MARKET HEALTH EARLY WARNING SYSTEM REPORT")
        print("="*60)
        print(f"\nTimestamp: {health_df['timestamp'].iloc[0]}")
        print(f"Platform Stress Level: {health_df['platform_stress_level'].iloc[0]:.2%}")
        print(f"Systemic Risk Index: {health_df['systemic_risk_index'].iloc[0]:.2%}")
        print(f"Alert Level: {health_df['alert_level'].iloc[0]}")
        print(f"Health Status: {health_df['health_status'].iloc[0]}")
        print(f"\nAlert Messages:\n{health_df['alert_messages'].iloc[0]}")
        print("\nModel Contributions:")
        print(f"  Model 1 (Suspicious Trades): {health_df['model1_stress_score'].iloc[0]:.2%}")
        print(f"  Model 2 (Position Exposure): {health_df['model2_stress_score'].iloc[0]:.2%}")
        print(f"  Model 3 (Token Forecasting): {health_df['model3_stress_score'].iloc[0]:.2%}")
        print(f"  Model 4 (Market Manipulation): {health_df['model4_stress_score'].iloc[0]:.2%}")
        print("\n" + "="*60)
        print("Model 5 completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"Error running Model 5: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Run Prediction Hub ML Models')
    parser.add_argument(
        '--model',
        type=int,
        choices=[4, 5],
        help='Model to run (4 or 5)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Run both models'
    )
    
    args = parser.parse_args()
    
    if args.all:
        run_model_4()
        print("\n")
        run_model_5()
    elif args.model == 4:
        run_model_4()
    elif args.model == 5:
        run_model_5()
    else:
        parser.print_help()
        print("\nExample usage:")
        print("  python run_models.py --model 4")
        print("  python run_models.py --model 5")
        print("  python run_models.py --all")


if __name__ == "__main__":
    main()

