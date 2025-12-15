// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title PredictionMarket
 * @dev A minimal viable prediction market contract for Polymarket-style platform
 */
contract PredictionMarket {
    struct Market {
        string title;
        uint256 endTime;
        bool resolved;
        bool outcome; // true = YES, false = NO
        address creator;
        uint256 totalLiquidity;
    }

    struct Trade {
        uint256 marketId;
        address user;
        bool outcome; // true = YES, false = NO
        uint256 amount;
        uint256 timestamp;
    }

    struct LiquidityEvent {
        uint256 marketId;
        address user;
        uint256 amount;
        uint256 timestamp;
    }

    // State variables
    mapping(uint256 => Market) public markets;
    mapping(uint256 => Trade) public trades;
    mapping(uint256 => LiquidityEvent) public liquidityEvents;
    
    uint256 public marketCounter;
    uint256 public tradeCounter;
    uint256 public liquidityCounter;
    
    address public owner;
    
    // Events
    event UserCreated(
        address indexed user,
        uint256 timestamp
    );
    
    event MarketCreated(
        uint256 indexed marketId,
        address indexed creator,
        uint256 endTime
    );
    
    event TradeExecuted(
        uint256 indexed marketId,
        address indexed user,
        bool outcome,
        uint256 amount,
        uint256 indexed tradeId
    );
    
    // Alias for TransactionCreated (maps to TradeExecuted)
    event TransactionCreated(
        uint256 indexed marketId,
        address indexed user,
        bool outcome,
        uint256 amount,
        uint256 indexed tradeId
    );
    
    event LiquidityAdded(
        uint256 indexed marketId,
        address indexed user,
        uint256 amount,
        uint256 indexed liquidityId
    );
    
    event MarketResolved(
        uint256 indexed marketId,
        bool outcome
    );

    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    modifier validMarket(uint256 marketId) {
        require(marketId > 0 && marketId <= marketCounter, "Invalid market");
        _;
    }

    modifier marketNotResolved(uint256 marketId) {
        require(!markets[marketId].resolved, "Market already resolved");
        _;
    }

    modifier marketNotEnded(uint256 marketId) {
        require(block.timestamp < markets[marketId].endTime, "Market ended");
        _;
    }

    constructor() {
        owner = msg.sender;
        // Emit UserCreated for contract owner
        emit UserCreated(msg.sender, block.timestamp);
    }

    /**
     * @dev Register a new user (emits UserCreated event)
     */
    function registerUser() external {
        emit UserCreated(msg.sender, block.timestamp);
    }
    
    /**
     * @dev Create a new prediction market
     * @param title Market title
     * @param endTime Unix timestamp when market ends
     */
    function createMarket(string memory title, uint256 endTime) external returns (uint256) {
        require(endTime > block.timestamp, "End time must be in the future");
        require(bytes(title).length > 0, "Title cannot be empty");
        
        // Emit UserCreated if this is first interaction
        // (In production, you'd track this in a mapping)
        emit UserCreated(msg.sender, block.timestamp);
        
        marketCounter++;
        markets[marketCounter] = Market({
            title: title,
            endTime: endTime,
            resolved: false,
            outcome: false,
            creator: msg.sender,
            totalLiquidity: 0
        });
        
        emit MarketCreated(marketCounter, msg.sender, endTime);
        return marketCounter;
    }

    /**
     * @dev Place a trade on a market
     * @param marketId The market ID
     * @param outcome true for YES, false for NO
     * @param amount Amount to stake
     */
    function placeTrade(uint256 marketId, bool outcome, uint256 amount) 
        external 
        validMarket(marketId)
        marketNotResolved(marketId)
        marketNotEnded(marketId)
        returns (uint256)
    {
        require(amount > 0, "Amount must be greater than 0");
        
        tradeCounter++;
        trades[tradeCounter] = Trade({
            marketId: marketId,
            user: msg.sender,
            outcome: outcome,
            amount: amount,
            timestamp: block.timestamp
        });
        
        emit TradeExecuted(marketId, msg.sender, outcome, amount, tradeCounter);
        // Also emit TransactionCreated for compatibility
        emit TransactionCreated(marketId, msg.sender, outcome, amount, tradeCounter);
        return tradeCounter;
    }

    /**
     * @dev Add liquidity to a market
     * @param marketId The market ID
     * @param amount Amount to add
     */
    function addLiquidity(uint256 marketId, uint256 amount) 
        external 
        validMarket(marketId)
        marketNotResolved(marketId)
        returns (uint256)
    {
        require(amount > 0, "Amount must be greater than 0");
        
        markets[marketId].totalLiquidity += amount;
        
        liquidityCounter++;
        liquidityEvents[liquidityCounter] = LiquidityEvent({
            marketId: marketId,
            user: msg.sender,
            amount: amount,
            timestamp: block.timestamp
        });
        
        emit LiquidityAdded(marketId, msg.sender, amount, liquidityCounter);
        return liquidityCounter;
    }

    /**
     * @dev Resolve a market (only owner can resolve)
     * @param marketId The market ID
     * @param outcome true for YES, false for NO
     */
    function resolveMarket(uint256 marketId, bool outcome) 
        external 
        onlyOwner
        validMarket(marketId)
        marketNotResolved(marketId)
    {
        require(
            block.timestamp >= markets[marketId].endTime,
            "Market has not ended yet"
        );
        
        markets[marketId].resolved = true;
        markets[marketId].outcome = outcome;
        
        emit MarketResolved(marketId, outcome);
    }

    /**
     * @dev Get market details
     */
    function getMarket(uint256 marketId) 
        external 
        view 
        returns (
            string memory title,
            uint256 endTime,
            bool resolved,
            bool outcome,
            address creator,
            uint256 totalLiquidity
        )
    {
        Market memory market = markets[marketId];
        return (
            market.title,
            market.endTime,
            market.resolved,
            market.outcome,
            market.creator,
            market.totalLiquidity
        );
    }

    /**
     * @dev Get trade details
     */
    function getTrade(uint256 tradeId) 
        external 
        view 
        returns (
            uint256 marketId,
            address user,
            bool outcome,
            uint256 amount,
            uint256 timestamp
        )
    {
        Trade memory trade = trades[tradeId];
        return (
            trade.marketId,
            trade.user,
            trade.outcome,
            trade.amount,
            trade.timestamp
        );
    }

    /**
     * @dev Get liquidity event details
     */
    function getLiquidityEvent(uint256 liquidityId) 
        external 
        view 
        returns (
            uint256 marketId,
            address user,
            uint256 amount,
            uint256 timestamp
        )
    {
        LiquidityEvent memory event_ = liquidityEvents[liquidityId];
        return (
            event_.marketId,
            event_.user,
            event_.amount,
            event_.timestamp
        );
    }
}

