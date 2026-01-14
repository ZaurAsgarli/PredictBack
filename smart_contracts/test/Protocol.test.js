const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Protocol V2 (5 Pillars)", function () {
    let deployer, user1, user2;
    let outcomeToken, amm, marketFactory, disputeBond, oracle;

    beforeEach(async function () {
        [deployer, user1, user2] = await ethers.getSigners();

        // 1. Deploy OutcomeToken
        const OutcomeToken = await ethers.getContractFactory("OutcomeToken");
        outcomeToken = await OutcomeToken.deploy(ethers.ZeroAddress);
        await outcomeToken.waitForDeployment();

        // 2. Deploy AMM
        const AMM = await ethers.getContractFactory("AMM");
        amm = await AMM.deploy(await outcomeToken.getAddress());
        await amm.waitForDeployment();

        // 3. Link
        await outcomeToken.setAMM(await amm.getAddress());

        // 4. Deploy Factory
        const MarketFactory = await ethers.getContractFactory("MarketFactory");
        marketFactory = await MarketFactory.deploy(await amm.getAddress());
        await marketFactory.waitForDeployment();

        // 5. Deploy Oracle
        const Oracle = await ethers.getContractFactory("Oracle");
        oracle = await Oracle.deploy(deployer.address);
        await oracle.waitForDeployment();
    });

    describe("Architecture Checks", function () {
        it("Should set the correct AMM address in Token", async function () {
            expect(await outcomeToken.amm()).to.equal(await amm.getAddress());
        });

        it("Should only allow AMM to mint tokens", async function () {
            // Direct mint should fail
            await expect(
                outcomeToken.mint(user1.address, 1, 100)
            ).to.be.revertedWith("Only AMM can mint/burn");
        });
    });

    describe("Market Creation Flow", function () {
        it("Should create a market via Factory", async function () {
            const initialLiquidity = ethers.parseEther("1");
            const title = "Will ETH hit 10k?";

            // Factory interacts with AMM to add liquidity, so we need value depending on AMM logic
            // Our mock AMM implementation takes value for addLiquidity.

            const tx = await marketFactory.createMarket(title, initialLiquidity, { value: initialLiquidity });
            const receipt = await tx.wait();

            // Check event
            const event = receipt.logs.find(x => {
                try { return marketFactory.interface.parseLog(x).name === "MarketCreated"; } catch (e) { return false; }
            });
            expect(event).to.not.be.undefined;
        });
    });

    describe("Oracle Resolution", function () {
        it("Should resolve market (mock)", async function () {
            const marketId = 12345; // Mock ID
            const outcome = ethers.encodeBytes32String("YES");

            await oracle.resolveMarket(marketId, outcome);

            expect(await oracle.resolved(marketId)).to.be.true;
            expect(await oracle.winningOutcome(marketId)).to.equal(outcome);
        });

        it("Should prevent non-resolver from resolving", async function () {
            await expect(
                oracle.connect(user1).resolveMarket(1, ethers.ZeroHash)
            ).to.be.revertedWith("Only resolver");
        });
    });
});
