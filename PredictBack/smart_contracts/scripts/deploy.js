const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const signers = await hre.ethers.getSigners();
  if (signers.length === 0) {
    throw new Error(
      "No signers available. Please set DEPLOYER_PRIVATE_KEY or PRIVATE_KEY in your .env file.\n" +
      "Example: DEPLOYER_PRIVATE_KEY=0x...your_private_key_here"
    );
  }
  const deployer = signers[0];
  console.log("Deploying contracts with account:", deployer.address);
  
  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("Account balance:", hre.ethers.formatEther(balance), "ETH");
  
  // Check if balance is sufficient (at least 0.001 ETH for deployment)
  if (balance < hre.ethers.parseEther("0.001")) {
    console.warn("⚠️  Warning: Account balance is very low. Deployment may fail.");
  }

  // Deploy PredictionMarket
  const PredictionMarket = await hre.ethers.getContractFactory("PredictionMarket");
  const predictionMarket = await PredictionMarket.deploy();
  await predictionMarket.waitForDeployment();

  const address = await predictionMarket.getAddress();
  console.log("PredictionMarket deployed to:", address);

  // Get network info early (needed for file writes)
  const network = await hre.ethers.provider.getNetwork();
  const networkName = network.name === "unknown" ? "sepolia" : network.name;
  const chainId = network.chainId.toString();

  // Get ABI
  const artifact = await hre.artifacts.readArtifact("PredictionMarket");
  const abi = artifact.abi;

  // Create directories if they don't exist
  const buildDir = path.join(__dirname, "..", "build");
  const deployedDir = path.join(__dirname, "..", "deployed");
  
  if (!fs.existsSync(buildDir)) {
    fs.mkdirSync(buildDir, { recursive: true });
  }
  if (!fs.existsSync(deployedDir)) {
    fs.mkdirSync(deployedDir, { recursive: true });
  }

  // Save ABI
  fs.writeFileSync(
    path.join(buildDir, "abi.json"),
    JSON.stringify(abi, null, 2)
  );
  console.log("ABI saved to build/abi.json");

  // Also copy ABI to backend utils/abis/
  const backendAbiDir = path.join(__dirname, "..", "..", "predicthub_backend", "utils", "abis");
  if (!fs.existsSync(backendAbiDir)) {
    fs.mkdirSync(backendAbiDir, { recursive: true });
  }
  fs.writeFileSync(
    path.join(backendAbiDir, "contract.json"),
    JSON.stringify({ 
      abi: abi, 
      address: address, 
      network: networkName, 
      chainId: chainId 
    }, null, 2)
  );
  console.log("ABI copied to backend utils/abis/contract.json");

  // Save deployment info
  const deploymentInfo = {
    network: networkName,
    chainId: chainId,
    address: address,
    deployer: deployer.address,
    deployedAt: new Date().toISOString(),
    abiHash: hre.ethers.keccak256(hre.ethers.toUtf8Bytes(JSON.stringify(abi))),
  };

  fs.writeFileSync(
    path.join(deployedDir, "contract.json"),
    JSON.stringify(deploymentInfo, null, 2)
  );
  console.log("Deployment info saved to deployed/contract.json");

  // Wait for a few block confirmations before verifying
  if (network.chainId !== 1337n && network.chainId !== 31337n) {
    console.log("Waiting for block confirmations...");
    await predictionMarket.deploymentTransaction().wait(5);
    
    try {
      await hre.run("verify:verify", {
        address: address,
        constructorArguments: [],
      });
      console.log("Contract verified on Etherscan");
    } catch (error) {
      console.log("Verification failed:", error.message);
    }
  }

  return { address, abi };
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });

