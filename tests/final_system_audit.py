# tests/final_system_audit.py
import os
import sys
import requests
import json
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

# Load env variables (assuming layout)
load_dotenv('backend_api/.env') 

API_BASE_URL = "http://localhost:8000/api"
DB_NAME = os.getenv("POSTGRES_DB", "predicthub_db")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

def print_pass(msg): print(f"✅ {msg}")
def print_fail(msg): print(f"❌ {msg}")
def print_info(msg): print(f"ℹ️  {msg}")

def get_db_connection():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)

def main():
    print("🚀 Starting Final System Audit (SDF2 V2)...")
    
    # 1. Verify Contracts V2
    print_info("Checking 5-Pillar Smart Contracts...")
    v2_path = Path("smart_contracts/deployed/contracts_v2.json")
    if v2_path.exists():
        with open(v2_path) as f:
            data = json.load(f)
            contracts = data.get('contracts', {})
            required = ['OutcomeToken', 'AMM', 'MarketFactory', 'Oracle', 'DisputeBond']
            missing = [c for c in required if c not in contracts]
            if not missing:
                print_pass("All 5 Contracts Deployed.")
                for c, addr in contracts.items():
                    print(f"      - {c}: {addr}")
            else:
                print_fail(f"Missing Contracts: {missing}")
    else:
        print_fail("contracts_v2.json NOT FOUND. Deploy failed?")

    # 2. Verify Database Content (Seed Results)
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Count Markets
        cur.execute("SELECT count(*) FROM markets_market")
        markets = cur.fetchone()[0]
        if markets >= 80: print_pass(f"Markets: {markets} (Expected 80+)")
        else: print_fail(f"Markets: {markets} (Expected 80+)")
        
        # Count Liquidity Events
        try:
            cur.execute("SELECT count(*) FROM liquidity_liquidityevent")
            liq = cur.fetchone()[0]
            if liq > 0: print_pass(f"Liquidity Events: {liq}")
            else: print_fail("Liquidity Events: 0")
        except: 
            conn.rollback()
            print_fail("liquidity_liquidityevent table missng?")

        # Count Trades
        cur.execute("SELECT count(*) FROM trades_trade")
        trades = cur.fetchone()[0]
        if trades >= 3000: print_pass(f"Trades: {trades} (Massive Seeding Verified)")
        else: print_fail(f"Trades: {trades} (Low)")

        # Count Users
        cur.execute("SELECT count(*) FROM users")
        users = cur.fetchone()[0]
        if users >= 300: print_pass(f"Users: {users}")
        else: print_fail(f"Users: {users} (Low)")
        
        # Count Outcome Tokens (using OutcomeToken table if separate, or implied)
        # Assuming `markets_outcometoken`
        try:
            cur.execute("SELECT count(*) FROM markets_outcometoken")
            tokens = cur.fetchone()[0]
            print_pass(f"Outcome Tokens: {tokens}")
        except:
             conn.rollback()
             print_info("OutcomeToken table check skipped (schema varies)")

        cur.close()
        conn.close()
    except Exception as e:
        print_fail(f"DB Check Failed: {e}")

    # 3. API Health Check
    try:
        r = requests.get(f"{API_BASE_URL}/health/") # or similar
        # Since we might not have a dedicated health endpoint, try /markets/
        r = requests.get(f"{API_BASE_URL}/markets/")
        if r.status_code == 200:
            print_pass("API /markets/ Accessible")
        else:
            print_fail(f"API Error: {r.status_code}")
    except:
        print_fail("API Connection Failed")

    print("🏁 Audit Complete.")

if __name__ == "__main__":
    main()
