# Deployment Guide for PredictionMarket Contract

## Prerequisites

1. **Node.js and npm** installed
2. **Sepolia ETH** in your deployer wallet (for gas fees)
3. **Alchemy API Key** (or other Sepolia RPC provider)

## Setup Steps

### 1. Install Dependencies

```bash
cd smart_contracts
npm install
```

### 2. Configure Environment Variables

Create a `.env` file in the `smart_contracts` directory (copy from `.env.example`):

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
# Alchemy Sepolia RPC URL (required)
ALCHEMY_SEPOLIA_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_ALCHEMY_API_KEY

# Deployer Private Key (required - must start with 0x and be 66 characters)
DEPLOYER_PRIVATE_KEY=0xYourPrivateKeyHere

# Etherscan API Key (optional - for contract verification)
ETHERSCAN_API_KEY=your_etherscan_api_key_here

# Network Selection (optional)
NETWORK=sepolia
```

**Important Security Notes:**
- ⚠️ **NEVER commit your `.env` file to git**
- ⚠️ **NEVER share your private key**
- The private key should be 66 characters total (including `0x` prefix)
- Example: `0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef`

### 3. Get Sepolia ETH

You need Sepolia testnet ETH to pay for gas. Get it from:
- [Sepolia Faucet](https://sepoliafaucet.com/)
- [Alchemy Sepolia Faucet](https://sepoliafaucet.com/)
- [Chainlink Faucet](https://faucets.chain.link/sepolia)

### 4. Compile Contracts

```bash
npx hardhat compile
```

### 5. Run Tests (Optional but Recommended)

```bash
npm test
```

All 20 tests should pass.

### 6. Deploy to Sepolia

```bash
npx hardhat run scripts/deploy.js --network sepolia
```

### Expected Output

If successful, you should see:

```
Deploying contracts with account: 0xYourAddress...
Account balance: 0.5 ETH
PredictionMarket deployed to: 0xContractAddress...
ABI saved to build/abi.json
ABI copied to backend utils/abis/contract.json
Deployment info saved to deployed/contract.json
Waiting for block confirmations...
Contract verified on Etherscan
```

### 7. Verify Deployment

After deployment, check:

1. **Contract on Etherscan**: Visit `https://sepolia.etherscan.io/address/0xYourContractAddress`

2. **Files Created**:
   - `smart_contracts/build/abi.json` - Raw ABI
   - `smart_contracts/deployed/contract.json` - Deployment metadata
   - `predicthub_backend/utils/abis/contract.json` - Backend-accessible contract info

3. **Backend Integration**: The Django backend will automatically load the contract address from `predicthub_backend/utils/abis/contract.json`

## Troubleshooting

### Error: "No signers available"

**Cause**: Private key not set or invalid in `.env`

**Solution**:
1. Check that `.env` file exists in `smart_contracts/` directory
2. Verify `DEPLOYER_PRIVATE_KEY` is set and starts with `0x`
3. Ensure private key is exactly 66 characters (including `0x`)

### Error: "insufficient funds"

**Cause**: Not enough Sepolia ETH for gas

**Solution**: Get more Sepolia ETH from a faucet (see step 3)

### Error: "network does not support EIP-1559"

**Cause**: Network configuration issue

**Solution**: Ensure `ALCHEMY_SEPOLIA_URL` is correct and points to Sepolia network

### Error: "Contract verification failed"

**Cause**: Etherscan API key missing or invalid

**Solution**: 
- This is optional - deployment still succeeds
- Set `ETHERSCAN_API_KEY` in `.env` if you want automatic verification

## Next Steps

After successful deployment:

1. **Update Backend Environment**: Set `CONTRACT_ADDRESS` in `predicthub_backend/.env` (optional - it will use the address from `contract.json`)

2. **Start Indexer**: 
   ```bash
   cd predicthub_backend
   python manage.py listen_events
   ```

3. **Backfill Historical Events**:
   ```bash
   python manage.py backfill --from-block 0 --to-block latest
   ```

## Security Reminders

- ✅ `.env` is in `.gitignore` - never commit it
- ✅ Use a dedicated wallet for deployment (not your main wallet)
- ✅ Keep your private key secure
- ✅ Consider using a hardware wallet for production deployments

