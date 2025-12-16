// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./OutcomeToken.sol";

contract AMM {
    OutcomeToken public outcomeToken;
    mapping(uint256 => uint256) public reserves; // marketId => liquidity

    event LiquidityAdded(address indexed user, uint256 marketId, uint256 amount);
    event LiquidityRemoved(address indexed user, uint256 marketId, uint256 amount);
    event Trade(address indexed user, uint256 marketId, bool isBuy, uint256 amount);

    constructor(address _outcomeToken) {
        outcomeToken = OutcomeToken(_outcomeToken);
    }

    function addLiquidity(uint256 marketId, uint256 amount) external payable {
        // Mock logic: accepting ETH as collateral
        reserves[marketId] += amount;
        emit LiquidityAdded(msg.sender, marketId, amount);
    }

    function removeLiquidity(uint256 marketId, uint256 amount) external {
        require(reserves[marketId] >= amount, "Insufficient liquidity");
        reserves[marketId] -= amount;
        emit LiquidityRemoved(msg.sender, marketId, amount);
    }

    function swap(uint256 marketId, bool isBuy, uint256 amount) external payable {
        // CPMM or LMSR logic would go here
        // For simple mock:
        emit Trade(msg.sender, marketId, isBuy, amount);
    }
}
