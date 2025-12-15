# Prediction Market Smart Contracts

Solidity smart contracts for the PredictHub prediction market platform.

---

## 📄 Contract: `PredictionMarket.sol`

### Overview

The `PredictionMarket` contract is the core smart contract that manages:
- Market creation and resolution
- Trading (YES/NO outcomes)
- Liquidity provision
- User registration

### Key Functions

#### Market Management

```solidity
function createMarket(string memory title, uint256 endTime) external returns (uint256)
```
Creates a new prediction market.
- **Emits**: `MarketCreated`, `UserCreated`
- **Returns**: Market ID

```solidity
function resolveMarket(uint256 marketId, bool outcome) external
```
Resolves a market (owner only).
- **Emits**: `MarketResolved`
- **Requires**: Market has ended, not already resolved

#### Trading

```solidity
function placeTrade(uint256 marketId, bool outcome, uint256 amount) external returns (uint256)
```
Places a trade on a market.
- **Emits**: `TradeExecuted`, `TransactionCreated`, `UserCreated`
- **Returns**: Trade ID

#### Liquidity

```solidity
function addLiquidity(uint256 marketId, uint256 amount) external returns (uint256)
```
Adds liquidity to a market.
- **Emits**: `LiquidityAdded`, `UserCreated`
- **Returns**: Liquidity event ID

---

## 📢 Events Emitted

### UserCreated

```solidity
event UserCreated(address indexed user, uint256 timestamp);
```

**Emitted when:**
- Market is created (creator)
- Trade is placed (trader)
- Liquidity is added (provider)

**Indexer Action**: Creates/updates user in `users_user` table.

### MarketCreated

```solidity
event MarketCreated(uint256 indexed marketId, address indexed creator, uint256 endTime);
```

**Emitted when:** Market is created.

**Indexer Action**: Creates market in `markets_market` table.

### TradeExecuted

```solidity
event TradeExecuted(
    uint256 indexed marketId,
    address indexed user,
    bool outcome,
    uint256 amount,
    uint256 indexed tradeId
);
```

**Alias**: `TransactionCreated` (same event, different name for compatibility).

**Emitted when:** Trade is placed.

**Indexer Action**: Creates trade in `trades_trade` table.

### LiquidityAdded

```solidity
event LiquidityAdded(
    uint256 indexed marketId,
    address indexed user,
    uint256 amount,
    uint256 indexed liquidityId
);
```

**Emitted when:** Liquidity is added to a market.

**Indexer Action**: Creates liquidity event in `liquidity_liquidityevent` table.

### MarketResolved

```solidity
event MarketResolved(uint256 indexed marketId, bool outcome);
```

**Emitted when:** Market is resolved by owner.

**Indexer Action**: Updates market resolution status in `markets_market` table.

---

## 🧪 Testing with Brownie

### Setup

```bash
# Install Brownie
pip install eth-brownie

# Verify installation
brownie --version
```

### Run Tests

```bash
# All tests (39 tests)
brownie test

# Only error paths (18 tests)
brownie test tests/test_prediction_market_error_paths.py

# Only success paths (21 tests)
brownie test tests/test_prediction_market.py

# With coverage
brownie test --coverage

# Verbose output
brownie test -v
```

### Test Coverage

- **Total**: 39 tests
- **Success Paths**: 21 tests
- **Error Paths**: 18 tests
  - Revert cases: 9 tests
  - Permission denial: 3 tests
  - Edge conditions: 6 tests

### Test Structure

```
tests/
├── test_prediction_market.py          # Success path tests
└── test_prediction_market_error_paths.py  # Error/failure tests
```

---

## 🚀 Deployment

### Using Hardhat (Recommended)

```bash
# Install dependencies
npm install

# Deploy to local network
npx hardhat run scripts/deploy_and_export.js --network localhost

# Deploy to Sepolia
npx hardhat run scripts/deploy_and_export.js --network sepolia
```

### Deployment Script (`scripts/deploy_and_export.js`)

The deployment script:
1. Deploys `PredictionMarket` contract
2. Saves ABI to `build/abi.json`
3. Exports contract info to `deployed/contract.json`
4. **Copies ABI to backend**: `../predicthub_backend/utils/abis/contract.json`

**Output Files:**
- `build/abi.json` - Contract ABI
- `deployed/contract.json` - Deployment details
- `../predicthub_backend/utils/abis/contract.json` - Backend ABI (for indexer)

### Contract Address

After deployment, update backend `.env`:
```bash
CONTRACT_ADDRESS=0x...
```

---

## 🔧 Configuration

### Brownie Config (`brownie-config.yaml`)

```yaml
compiler:
  solc:
    version: "0.8.20"
    optimizer:
      enabled: true
      runs: 200

networks:
  development:
    cmd_settings:
      host: 127.0.0.1
      port: 8545
  sepolia:
    cmd_settings:
      host: https://sepolia.infura.io/v3/$WEB3_INFURA_PROJECT_ID
```

### Hardhat Config (`hardhat.config.js`)

```javascript
module.exports = {
  solidity: "0.8.20",
  networks: {
    sepolia: {
      url: `https://sepolia.infura.io/v3/${process.env.WEB3_INFURA_PROJECT_ID}`,
      accounts: [process.env.PRIVATE_KEY]
    }
  }
};
```

---

## 📝 Contract Functions Reference

### Getters

```solidity
function getMarket(uint256 marketId) external view returns (
    string memory title,
    uint256 endTime,
    bool resolved,
    bool outcome,
    address creator,
    uint256 totalLiquidity
)

function getTrade(uint256 tradeId) external view returns (
    uint256 marketId,
    address user,
    bool outcome,
    uint256 amount,
    uint256 timestamp
)

function getLiquidityEvent(uint256 liquidityId) external view returns (
    uint256 marketId,
    address user,
    uint256 amount,
    uint256 timestamp
)
```

### State Variables

```solidity
uint256 public marketCounter;      // Total markets created
uint256 public tradeCounter;        // Total trades executed
uint256 public liquidityCounter;    // Total liquidity events
address public owner;               // Contract owner
```

---

## 🔒 Access Control

### Owner-Only Functions

- `resolveMarket()` - Only owner can resolve markets

### Modifiers

- `validMarket(uint256 marketId)` - Ensures market exists
- `marketNotResolved(uint256 marketId)` - Ensures market not resolved
- `marketNotEnded(uint256 marketId)` - Ensures market not ended
- `onlyOwner` - Ensures caller is owner

---

## 🐛 Common Issues

### "Contract not found"

```bash
# Compile contract
brownie compile

# Or with Hardhat
npx hardhat compile
```

### "Network not found"

Check `brownie-config.yaml` or `hardhat.config.js` network settings.

### "Insufficient funds"

Ensure your account has enough ETH for gas:
```bash
# Check balance (Brownie console)
brownie console
>>> accounts[0].balance()
```

---

## 📚 Related Documentation

- **Backend Integration**: See `../predicthub_backend/README.md`
- **Testing Guide**: See `../TESTING_GUIDE.md`
- **Brownie Docs**: https://eth-brownie.readthedocs.io/

---

## 🚀 Quick Commands

```bash
# Compile
brownie compile

# Test
brownie test

# Deploy (Hardhat)
npx hardhat run scripts/deploy_and_export.js --network localhost

# Console (interactive)
brownie console
>>> prediction_market = PredictionMarket.deploy({'from': accounts[0]})
>>> prediction_market.createMarket("Test", chain.time() + 86400, {'from': accounts[1]})
```
