/**
 * Deployment script that exports ABI and contract address to backend-readable file
 * This script deploys the contract and saves the ABI and address to a JSON file
 * that the Django backend can read.
 */

const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("Deploying PredictionMarket contract...");

  // Get the contract factory
  const PredictionMarket = await hre.ethers.getContractFactory("PredictionMarket");
  
  // Deploy the contract
  const predictionMarket = await PredictionMarket.deploy();
  await predictionMarket.waitForDeployment();

  const contractAddress = await predictionMarket.getAddress();
  console.log("PredictionMarket deployed to:", contractAddress);

  // Get the contract ABI
  const contractArtifact = await hre.artifacts.readArtifact("PredictionMarket");
  const abi = contractArtifact.abi;

  // Prepare deployment data
  const deploymentData = {
    contractAddress: contractAddress,
    abi: abi,
    network: hre.network.name,
    chainId: (await hre.ethers.provider.getNetwork()).chainId,
    deployedAt: new Date().toISOString(),
    deployer: (await hre.ethers.getSigners())[0].address,
  };

  // Save to deployed/contract.json (for backend)
  const deployedPath = path.join(__dirname, "..", "deployed", "contract.json");
  fs.writeFileSync(deployedPath, JSON.stringify(deploymentData, null, 2));
  console.log("Deployment data saved to:", deployedPath);

  // Also save ABI separately to utils/abi/ (for backend compatibility)
  const abiPath = path.join(__dirname, "..", "..", "predicthub_backend", "utils", "abi", "PredictionMarket.json");
  const abiDir = path.dirname(abiPath);
  if (!fs.existsSync(abiDir)) {
    fs.mkdirSync(abiDir, { recursive: true });
  }
  fs.writeFileSync(abiPath, JSON.stringify(abi, null, 2));
  console.log("ABI saved to:", abiPath);

  // Save contract address to environment file format
  const envPath = path.join(__dirname, "..", "deployed", ".env.contract");
  const envContent = `CONTRACT_ADDRESS=${contractAddress}\nNETWORK=${hre.network.name}\nCHAIN_ID=${(await hre.ethers.provider.getNetwork()).chainId}\n`;
  fs.writeFileSync(envPath, envContent);
  console.log("Environment variables saved to:", envPath);

  console.log("\n✅ Deployment complete!");
  console.log("Contract Address:", contractAddress);
  console.log("Network:", hre.network.name);
  console.log("\nBackend can now read contract data from:");
  console.log("  - deployed/contract.json");
  console.log("  - utils/abi/PredictionMarket.json");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });

