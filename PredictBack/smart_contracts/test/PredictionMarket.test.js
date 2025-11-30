const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("PredictionMarket", function () {
  let predictionMarket;
  let owner;
  let user1;
  let user2;
  let user3;

  beforeEach(async function () {
    [owner, user1, user2, user3] = await ethers.getSigners();

    const PredictionMarket = await ethers.getContractFactory("PredictionMarket");
    predictionMarket = await PredictionMarket.deploy();
    await predictionMarket.waitForDeployment();
  });

  describe("Deployment", function () {
    it("Should set the right owner", async function () {
      expect(await predictionMarket.owner()).to.equal(owner.address);
    });

    it("Should start with zero markets", async function () {
      expect(await predictionMarket.marketCounter()).to.equal(0);
    });
  });

  describe("Market Creation - Success", function () {
    it("Should create a market successfully", async function () {
      const currentBlock = await ethers.provider.getBlock('latest');
      const endTime = currentBlock.timestamp + 86400; // 24 hours from current block time
      const title = "Test Market";
      const tx = await predictionMarket.connect(user1).createMarket(title, endTime);
      const receipt = await tx.wait();

      expect(await predictionMarket.marketCounter()).to.equal(1);
      
      // Check MarketCreated event
      const event = receipt.logs.find(log => {
        try {
          const parsed = predictionMarket.interface.parseLog(log);
          return parsed.name === "MarketCreated";
        } catch {
          return false;
        }
      });
      
      expect(event).to.not.be.undefined;
      const parsedEvent = predictionMarket.interface.parseLog(event);
      expect(parsedEvent.args.marketId).to.equal(1);
      expect(parsedEvent.args.creator).to.equal(user1.address);
      expect(parsedEvent.args.endTime).to.equal(endTime);
      
      // Check stored market data
      const market = await predictionMarket.getMarket(1);
      expect(market.title).to.equal(title);
      expect(market.creator).to.equal(user1.address);
      expect(market.endTime).to.equal(endTime);
      expect(market.resolved).to.equal(false);
      expect(market.outcome).to.equal(false);
      expect(market.totalLiquidity).to.equal(0);
    });
  });

  describe("Market Creation - Failures", function () {
    it("Should revert if endTime is in the past", async function () {
      const currentBlock = await ethers.provider.getBlock('latest');
      const pastTime = currentBlock.timestamp - 86400; // 24 hours in the past
      await expect(
        predictionMarket.connect(user1).createMarket("Test Market", pastTime)
      ).to.be.revertedWith("End time must be in the future");
    });

    it("Should revert if title is empty", async function () {
      const currentBlock = await ethers.provider.getBlock('latest');
      const endTime = currentBlock.timestamp + 86400; // 24 hours from current block time
      await expect(
        predictionMarket.connect(user1).createMarket("", endTime)
      ).to.be.revertedWith("Title cannot be empty");
    });
  });

  describe("Trading - Success", function () {
    let marketId;
    let endTime;

    beforeEach(async function () {
      endTime = Math.floor(Date.now() / 1000) + 86400;
      const tx = await predictionMarket.connect(user1).createMarket("Test Market", endTime);
      await tx.wait();
      marketId = 1;
    });

    it("Should place a trade successfully", async function () {
      const amount = ethers.parseEther("1.0");
      const outcome = true; // YES
      const tx = await predictionMarket.connect(user2).placeTrade(marketId, outcome, amount);
      const receipt = await tx.wait();

      expect(await predictionMarket.tradeCounter()).to.equal(1);
      
      // Check TradeExecuted event
      const event = receipt.logs.find(log => {
        try {
          const parsed = predictionMarket.interface.parseLog(log);
          return parsed.name === "TradeExecuted";
        } catch {
          return false;
        }
      });
      
      expect(event).to.not.be.undefined;
      const parsedEvent = predictionMarket.interface.parseLog(event);
      expect(parsedEvent.args.marketId).to.equal(marketId);
      expect(parsedEvent.args.user).to.equal(user2.address);
      expect(parsedEvent.args.outcome).to.equal(outcome);
      expect(parsedEvent.args.amount).to.equal(amount);
      expect(parsedEvent.args.tradeId).to.equal(1);
      
      // Check stored trade data
      const trade = await predictionMarket.getTrade(1);
      expect(trade.marketId).to.equal(marketId);
      expect(trade.user).to.equal(user2.address);
      expect(trade.outcome).to.equal(outcome);
      expect(trade.amount).to.equal(amount);
    });
  });

  describe("Trading - Failures", function () {
    let marketId;
    let endTime;

    beforeEach(async function () {
      endTime = Math.floor(Date.now() / 1000) + 86400;
      const tx = await predictionMarket.connect(user1).createMarket("Test Market", endTime);
      await tx.wait();
      marketId = 1;
    });

    it("Should revert if amount is zero", async function () {
      await expect(
        predictionMarket.connect(user2).placeTrade(marketId, true, 0)
      ).to.be.revertedWith("Amount must be greater than 0");
    });

    it("Should revert if market ID is invalid", async function () {
      await expect(
        predictionMarket.connect(user2).placeTrade(999, true, ethers.parseEther("1.0"))
      ).to.be.revertedWith("Invalid market");
    });

    it("Should revert if market has ended", async function () {
      // Create a new market with a short end time
      const currentBlock = await ethers.provider.getBlock('latest');
      const shortEndTime = currentBlock.timestamp + 3600; // 1 hour in the future
      const tx = await predictionMarket.connect(user1).createMarket("Short Market", shortEndTime);
      await tx.wait();
      const shortMarketId = 2;
      
      // Advance time past the market end time
      await ethers.provider.send("evm_increaseTime", [7200]); // Advance 2 hours
      await ethers.provider.send("evm_mine", []);

      // Now try to place a trade - should fail because market has ended
      await expect(
        predictionMarket.connect(user2).placeTrade(shortMarketId, true, ethers.parseEther("1.0"))
      ).to.be.revertedWith("Market ended");
    });

    it("Should revert if market is resolved", async function () {
      // Advance time and resolve the market
      await ethers.provider.send("evm_increaseTime", [86400]);
      await ethers.provider.send("evm_mine", []);
      
      await predictionMarket.connect(owner).resolveMarket(marketId, true);

      await expect(
        predictionMarket.connect(user2).placeTrade(marketId, true, ethers.parseEther("1.0"))
      ).to.be.revertedWith("Market already resolved");
    });
  });

  describe("Liquidity - Success", function () {
    let marketId;
    let endTime;

    beforeEach(async function () {
      const currentBlock = await ethers.provider.getBlock('latest');
      endTime = currentBlock.timestamp + 86400; // 24 hours from current block time
      const tx = await predictionMarket.connect(user1).createMarket("Test Market", endTime);
      await tx.wait();
      marketId = 1;
    });

    it("Should add liquidity successfully", async function () {
      const amount = ethers.parseEther("10.0");
      const tx = await predictionMarket.connect(user2).addLiquidity(marketId, amount);
      const receipt = await tx.wait();

      expect(await predictionMarket.liquidityCounter()).to.equal(1);
      
      // Check stored market liquidity
      const market = await predictionMarket.getMarket(marketId);
      expect(market.totalLiquidity).to.equal(amount);
      
      // Check LiquidityAdded event
      const event = receipt.logs.find(log => {
        try {
          const parsed = predictionMarket.interface.parseLog(log);
          return parsed.name === "LiquidityAdded";
        } catch {
          return false;
        }
      });
      
      expect(event).to.not.be.undefined;
      const parsedEvent = predictionMarket.interface.parseLog(event);
      expect(parsedEvent.args.marketId).to.equal(marketId);
      expect(parsedEvent.args.user).to.equal(user2.address);
      expect(parsedEvent.args.amount).to.equal(amount);
      expect(parsedEvent.args.liquidityId).to.equal(1);
    });
  });

  describe("Liquidity - Failures", function () {
    let marketId;
    let endTime;

    beforeEach(async function () {
      const currentBlock = await ethers.provider.getBlock('latest');
      endTime = currentBlock.timestamp + 86400; // 24 hours from current block time
      const tx = await predictionMarket.connect(user1).createMarket("Test Market", endTime);
      await tx.wait();
      marketId = 1;
    });

    it("Should revert if amount is zero", async function () {
      await expect(
        predictionMarket.connect(user2).addLiquidity(marketId, 0)
      ).to.be.revertedWith("Amount must be greater than 0");
    });

    it("Should revert if market is resolved", async function () {
      await ethers.provider.send("evm_increaseTime", [86400]);
      await ethers.provider.send("evm_mine", []);
      
      await predictionMarket.connect(owner).resolveMarket(marketId, true);

      await expect(
        predictionMarket.connect(user2).addLiquidity(marketId, ethers.parseEther("1.0"))
      ).to.be.revertedWith("Market already resolved");
    });
  });

  describe("Market Resolution - Success", function () {
    let marketId;
    let endTime;

    beforeEach(async function () {
      const currentBlock = await ethers.provider.getBlock('latest');
      endTime = currentBlock.timestamp + 86400; // 24 hours from current block time
      const tx = await predictionMarket.connect(user1).createMarket("Test Market", endTime);
      await tx.wait();
      marketId = 1;
    });

    it("Should resolve market successfully", async function () {
      await ethers.provider.send("evm_increaseTime", [86400]);
      await ethers.provider.send("evm_mine", []);
      
      const outcome = true; // YES
      const tx = await predictionMarket.connect(owner).resolveMarket(marketId, outcome);
      const receipt = await tx.wait();

      const market = await predictionMarket.getMarket(marketId);
      expect(market.resolved).to.equal(true);
      expect(market.outcome).to.equal(outcome);
      
      // Check MarketResolved event
      const event = receipt.logs.find(log => {
        try {
          const parsed = predictionMarket.interface.parseLog(log);
          return parsed.name === "MarketResolved";
        } catch {
          return false;
        }
      });
      
      expect(event).to.not.be.undefined;
      const parsedEvent = predictionMarket.interface.parseLog(event);
      expect(parsedEvent.args.marketId).to.equal(marketId);
      expect(parsedEvent.args.outcome).to.equal(outcome);
    });
  });

  describe("Market Resolution - Failures", function () {
    let marketId;
    let endTime;

    beforeEach(async function () {
      const currentBlock = await ethers.provider.getBlock('latest');
      endTime = currentBlock.timestamp + 86400; // 24 hours from current block time
      const tx = await predictionMarket.connect(user1).createMarket("Test Market", endTime);
      await tx.wait();
      marketId = 1;
    });

    it("Should revert if not owner", async function () {
      await ethers.provider.send("evm_increaseTime", [86400]);
      await ethers.provider.send("evm_mine", []);
      
      await expect(
        predictionMarket.connect(user1).resolveMarket(marketId, true)
      ).to.be.revertedWith("Not owner");
    });

    it("Should revert if market has not ended", async function () {
      await expect(
        predictionMarket.connect(owner).resolveMarket(marketId, true)
      ).to.be.revertedWith("Market has not ended yet");
    });

    it("Should revert if market already resolved", async function () {
      await ethers.provider.send("evm_increaseTime", [86400]);
      await ethers.provider.send("evm_mine", []);
      
      await predictionMarket.connect(owner).resolveMarket(marketId, true);

      await expect(
        predictionMarket.connect(owner).resolveMarket(marketId, false)
      ).to.be.revertedWith("Market already resolved");
    });
  });

  describe("Getters", function () {
    let marketId;
    let endTime;

    beforeEach(async function () {
      const currentBlock = await ethers.provider.getBlock('latest');
      endTime = currentBlock.timestamp + 86400; // 24 hours from current block time
      const tx = await predictionMarket.connect(user1).createMarket("Test Market", endTime);
      await tx.wait();
      marketId = 1;
    });

    it("Should return correct market details", async function () {
      const market = await predictionMarket.getMarket(marketId);
      expect(market.title).to.equal("Test Market");
      expect(market.creator).to.equal(user1.address);
      expect(market.resolved).to.equal(false);
    });

    it("Should return correct trade details", async function () {
      const amount = ethers.parseEther("1.0");
      await predictionMarket.connect(user2).placeTrade(marketId, true, amount);
      
      const trade = await predictionMarket.getTrade(1);
      expect(trade.marketId).to.equal(marketId);
      expect(trade.user).to.equal(user2.address);
      expect(trade.outcome).to.equal(true);
      expect(trade.amount).to.equal(amount);
    });

    it("Should return correct liquidity event details", async function () {
      const amount = ethers.parseEther("10.0");
      await predictionMarket.connect(user2).addLiquidity(marketId, amount);
      
      const event = await predictionMarket.getLiquidityEvent(1);
      expect(event.marketId).to.equal(marketId);
      expect(event.user).to.equal(user2.address);
      expect(event.amount).to.equal(amount);
    });
  });
});
