require("@nomicfoundation/hardhat-toolbox");
require("@nomicfoundation/hardhat-verify");
require("dotenv").config();

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },
  networks: {
    hardhat: {
      chainId: 1337,
    },
    localhost: {
      url: "http://127.0.0.1:8545",
      chainId: 1337,
    },
    sepolia: {
      url: process.env.ALCHEMY_SEPOLIA_URL || process.env.SEPOLIA_RPC_URL || "https://eth-sepolia.g.alchemy.com/v2/YOUR_API_KEY",
      accounts: (() => {
        // Check for DEPLOYER_PRIVATE_KEY first, then PRIVATE_KEY
        const key = process.env.DEPLOYER_PRIVATE_KEY || process.env.PRIVATE_KEY;
        if (!key) {
          return []; // Empty array - will fail with helpful error in deploy script
        }
        // Validate private key format (should be 66 chars with 0x prefix, or 64 without)
        const cleanKey = key.startsWith('0x') ? key : `0x${key}`;
        if (cleanKey.length !== 66) {
          console.warn(`⚠️  Warning: Private key length is ${cleanKey.length}, expected 66 (with 0x prefix)`);
          return []; // Invalid format
        }
        return [cleanKey];
      })(),
      chainId: 11155111,
    },
  },
  etherscan: {
    apiKey: process.env.ETHERSCAN_API_KEY || "",
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts",
  },
};

