"""
Simulation script for testing guide.

This script simulates blockchain transactions for manual testing.
Run this after deploying the contract and starting the indexer.
"""

from brownie import PredictionMarket, accounts, chain
import time

def simulate_user_flow():
    """Simulate: Create market → Add liquidity → Place trade"""
    
    print("=" * 60)
    print("Simulating User Flow: Market Creation → Liquidity → Trade")
    print("=" * 60)
    
    # Get deployed contract
    try:
        prediction_market = PredictionMarket[-1]
        print(f"✅ Contract found: {prediction_market.address}")
    except:
        print("❌ Contract not found. Deploy first with: npx hardhat run scripts/deploy_and_export.js")
        return
    
    # Get accounts
    creator = accounts[1]
    liquidity_provider = accounts[2]
    trader = accounts[3]
    
    print(f"\n📝 Step 1: Creating market...")
    print(f"   Creator: {creator.address}")
    
    # Create market
    end_time = chain.time() + 86400  # 24 hours
    tx1 = prediction_market.createMarket(
        "Test Market: Will Ethereum reach $5000 by 2025?",
        end_time,
        {'from': creator}
    )
    
    market_id = prediction_market.marketCounter()
    print(f"   ✅ Market created! ID: {market_id}")
    print(f"   Transaction: {tx1.txid}")
    
    time.sleep(2)  # Wait for indexer to process
    
    print(f"\n💰 Step 2: Adding liquidity...")
    print(f"   Provider: {liquidity_provider.address}")
    print(f"   Amount: 10 ETH")
    
    # Add liquidity
    tx2 = prediction_market.addLiquidity(
        market_id,
        "10 ether",
        {'from': liquidity_provider}
    )
    
    liquidity_id = prediction_market.liquidityCounter()
    print(f"   ✅ Liquidity added! ID: {liquidity_id}")
    print(f"   Transaction: {tx2.txid}")
    
    time.sleep(2)  # Wait for indexer to process
    
    print(f"\n📊 Step 3: Placing trade...")
    print(f"   Trader: {trader.address}")
    print(f"   Outcome: YES")
    print(f"   Amount: 1 ETH")
    
    # Place trade
    tx3 = prediction_market.placeTrade(
        market_id,
        True,  # YES
        "1 ether",
        {'from': trader}
    )
    
    trade_id = prediction_market.tradeCounter()
    print(f"   ✅ Trade placed! ID: {trade_id}")
    print(f"   Transaction: {tx3.txid}")
    
    print(f"\n" + "=" * 60)
    print("✅ Simulation Complete!")
    print("=" * 60)
    print(f"\n📋 Summary:")
    print(f"   Market ID: {market_id}")
    print(f"   Liquidity ID: {liquidity_id}")
    print(f"   Trade ID: {trade_id}")
    print(f"\n🔍 Next Steps:")
    print(f"   1. Check indexer terminal for event processing logs")
    print(f"   2. Query database: SELECT * FROM markets_market WHERE onchain_market_id = {market_id}")
    print(f"   3. Check API: curl http://localhost:8000/api/markets/{market_id}/")
    print(f"\n⏱️  Wait 5-10 seconds for indexer to process events...")

if __name__ == "__main__":
    simulate_user_flow()

