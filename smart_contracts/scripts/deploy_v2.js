const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
    const signers = await hre.ethers.getSigners();
    const deployer = signers[0];
    console.log("Deploying V2 (5-Pillar) contracts with:", deployer.address);

    // 1. Deploy AMM
    // Note: AMM needs OutcomeToken, but OutcomeToken needs AMM (circular).
    // Strategy: Deploy AMM with dummy text, Deploy Token with AMM, Set Token on AMM.
    // Actually, typical pattern: OutcomeToken deploys first with authorized minter? 
    // Code shows: OutcomeToken takes AMM in constructor. AMM takes OutcomeToken in constructor. 
    // We need to decoupling or use `setAMM` / `setOutcomeToken`.

    // Checking code: OutcomeToken takes `_amm`. AMM takes `_outcomeToken`.
    // Solution: 
    // 1. Deploy OutcomeToken(address(0))
    // 2. Deploy AMM(OutcomeToken.address)
    // 3. OutcomeToken.setAMM(AMM.address)

    // Deploy OutcomeToken
    const OutcomeToken = await hre.ethers.getContractFactory("OutcomeToken");
    // Pass zero address initially if constructor requires it, or modify constructor. 
    // Assuming constructor(address _amm).
    const outcomeToken = await OutcomeToken.deploy(hre.ethers.ZeroAddress);
    await outcomeToken.waitForDeployment();
    const tokenAddr = await outcomeToken.getAddress();
    console.log("OutcomeToken deployed to:", tokenAddr);

    // Deploy AMM
    const AMM = await hre.ethers.getContractFactory("AMM");
    const amm = await AMM.deploy(tokenAddr);
    await amm.waitForDeployment();
    const ammAddr = await amm.getAddress();
    console.log("AMM deployed to:", ammAddr);

    // Link Token -> AMM
    await outcomeToken.setAMM(ammAddr);
    console.log("OutcomeToken linked to AMM");

    // Deploy MarketFactory
    const MarketFactory = await hre.ethers.getContractFactory("MarketFactory");
    const factory = await MarketFactory.deploy(ammAddr);
    await factory.waitForDeployment();
    const factoryAddr = await factory.getAddress();
    console.log("MarketFactory deployed to:", factoryAddr);

    // Deploy DisputeBond
    const DisputeBond = await hre.ethers.getContractFactory("DisputeBond");
    const dispute = await DisputeBond.deploy();
    await dispute.waitForDeployment();
    const disputeAddr = await dispute.getAddress();
    console.log("DisputeBond deployed to:", disputeAddr);

    // Deploy Oracle
    const Oracle = await hre.ethers.getContractFactory("Oracle");
    // Resolver is deployer for now
    const oracle = await Oracle.deploy(deployer.address);
    await oracle.waitForDeployment();
    const oracleAddr = await oracle.getAddress();
    console.log("Oracle deployed to:", oracleAddr);

    // SAVE DEPLOYMENT INFO
    const deploymentInfo = {
        network: (await hre.ethers.provider.getNetwork()).name,
        contracts: {
            OutcomeToken: tokenAddr,
            AMM: ammAddr,
            MarketFactory: factoryAddr,
            DisputeBond: disputeAddr,
            Oracle: oracleAddr
        },
        deployedAt: new Date().toISOString()
    };

    const deployedDir = path.join(__dirname, "..", "deployed");
    if (!fs.existsSync(deployedDir)) fs.mkdirSync(deployedDir, { recursive: true });

    fs.writeFileSync(
        path.join(deployedDir, "contracts_v2.json"),
        JSON.stringify(deploymentInfo, null, 2)
    );
    console.log("Deployment V2 info saved to deployed/contracts_v2.json");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
