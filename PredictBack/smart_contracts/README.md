# Prediction Market Smart Contracts

Smart contracts for the PredictHub prediction market platform.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create `.env` file:
```bash
cp .env.example .env
# Edit .env with your keys
```

## Compile

```bash
npm run compile
```

## Test

```bash
npm test
```

## Deploy

### Local (Hardhat)
```bash
npm run deploy:local
```

### Sepolia
```bash
npm run deploy:sepolia
```

## Contract Address

After deployment, contract information is stored in:
- `build/abi.json` - Contract ABI
- `deployed/contract.json` - Deployment details (address, network, etc.)

## Contract Functions

### createMarket(string title, uint256 endTime)
Creates a new prediction market.

### placeTrade(uint256 marketId, bool outcome, uint256 amount)
Places a trade on a market. `outcome` is `true` for YES, `false` for NO.

### addLiquidity(uint256 marketId, uint256 amount)
Adds liquidity to a market.

### resolveMarket(uint256 marketId, bool outcome)
Resolves a market (owner only). `outcome` is `true` for YES, `false` for NO.

## Events

- `MarketCreated(uint256 indexed marketId, address indexed creator, uint256 endTime)`
- `TradePlaced(uint256 indexed marketId, address indexed user, bool outcome, uint256 amount, uint256 indexed tradeId)`
- `LiquidityAdded(uint256 indexed marketId, address indexed user, uint256 amount, uint256 indexed liquidityId)`
- `MarketResolved(uint256 indexed marketId, bool outcome)`

