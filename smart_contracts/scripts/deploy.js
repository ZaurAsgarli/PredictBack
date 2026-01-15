const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
    const signers = await hre.ethers.getSigners();
    const deployer = signers[0];
    console.log("🚀 Deploying Protocol V2 with account:", deployer.address);

    const network = await hre.ethers.provider.getNetwork();
    const networkName = network.name === "unknown" ? "localhost" : network.name;

    // --- 1. DEPLOYMENT ---

    // A. OutcomeToken (initially 0x0 AMM)
    const OutcomeToken = await hre.ethers.getContractFactory("OutcomeToken");
    const outcomeToken = await OutcomeToken.deploy(hre.ethers.ZeroAddress);
    await outcomeToken.waitForDeployment();
    const tokenAddr = await outcomeToken.getAddress();
    console.log("✅ OutcomeToken deployed to:", tokenAddr);

    // B. AMM (depends on Token)
    const AMM = await hre.ethers.getContractFactory("AMM");
    const amm = await AMM.deploy(tokenAddr);
    await amm.waitForDeployment();
    const ammAddr = await amm.getAddress();
    console.log("✅ AMM deployed to:", ammAddr);

    // C. Link Token -> AMM
    try {
        const tx = await outcomeToken.setAMM(ammAddr);
        await tx.wait();
        console.log("🔗 OutcomeToken linked to AMM");
    } catch (e) {
        console.error("Warning: Failed to link AMM (Already set?):", e.message);
    }

    // D. MarketFactory (depends on AMM)
    const MarketFactory = await hre.ethers.getContractFactory("MarketFactory");
    const factory = await MarketFactory.deploy(ammAddr);
    await factory.waitForDeployment();
    const factoryAddr = await factory.getAddress();
    console.log("✅ MarketFactory deployed to:", factoryAddr);

    // E. DisputeBond (Independent)
    const DisputeBond = await hre.ethers.getContractFactory("DisputeBond");
    const dispute = await DisputeBond.deploy();
    await dispute.waitForDeployment();
    const disputeAddr = await dispute.getAddress();
    console.log("✅ DisputeBond deployed to:", disputeAddr);

    // F. Oracle (Independent, Resolver = Deployer)
    const Oracle = await hre.ethers.getContractFactory("Oracle");
    const oracle = await Oracle.deploy(deployer.address);
    await oracle.waitForDeployment();
    const oracleAddr = await oracle.getAddress();
    console.log("✅ Oracle deployed to:", oracleAddr);


    // --- 2. ARTIFACT EXPORT ---

    const artifactsDir = path.join(__dirname, "..", "deployed");
    if (!fs.existsSync(artifactsDir)) fs.mkdirSync(artifactsDir, { recursive: true });

    const deploymentData = {
        network: networkName,
        chainId: network.chainId.toString(),
        deployedAt: new Date().toISOString(),
        contracts: {
            OutcomeToken: tokenAddr,
            AMM: ammAddr,
            MarketFactory: factoryAddr,
            DisputeBond: disputeAddr,
            Oracle: oracleAddr
        }
    };

    // Save main deployment JSON
    fs.writeFileSync(
        path.join(artifactsDir, "contracts.json"),
        JSON.stringify(deploymentData, null, 2)
    );
    console.log(`💾 Contracts Saved: ${path.join(artifactsDir, "contracts.json")}`);


    // --- 3. LOCAL LOGGING (CRITICAL) ---

    const logsDir = path.join(__dirname, "..", "logs");
    if (!fs.existsSync(logsDir)) fs.mkdirSync(logsDir, { recursive: true });

    const logEntry = `[${new Date().toISOString()}] [${networkName}] Deployed Protocol V2\n` +
        `   - Factory: ${factoryAddr}\n` +
        `   - AMM: ${ammAddr}\n` +
        `   - Token: ${tokenAddr}\n` +
        `   - Oracle: ${oracleAddr}\n` +
        `   - Bond: ${disputeAddr}\n` +
        `   - Deployer: ${deployer.address}\n` +
        `--------------------------------------------------\n`;

    fs.appendFileSync(path.join(logsDir, "deployment_history.log"), logEntry);
    console.log(`📝 Log Appended: ${path.join(logsDir, "deployment_history.log")}`);

    // --- 4. VERIFICATION (Optional) ---
    if (networkName !== "localhost" && networkName !== "hardhat") {
        console.log("Waiting for blocks before verification...");
        // await new Promise(r => setTimeout(r, 10000));
        // hre.run("verify:verify", ...)
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
