// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./AMM.sol";

contract MarketFactory {
    AMM public amm;
    event MarketCreated(uint256 indexed marketId, string name, address indexed creator);

    constructor(address _amm) {
        amm = AMM(_amm);
    }

    function createMarket(string memory name, uint256 initialLiquidity) external payable {
        // Ideally this creates a struct or child contract
        // Mock ID generation
        uint256 marketId = uint256(keccak256(abi.encodePacked(name, block.timestamp)));
        
        if (initialLiquidity > 0) {
            amm.addLiquidity{value: msg.value}(marketId, initialLiquidity);
        }
        
        emit MarketCreated(marketId, name, msg.sender);
    }
}
