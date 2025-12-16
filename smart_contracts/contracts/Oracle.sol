// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Oracle {
    mapping(uint256 => bool) public resolved;
    mapping(uint256 => bytes32) public winningOutcome;
    address public resolver;

    event MarketResolved(uint256 indexed marketId, bytes32 outcome);

    constructor(address _resolver) {
        resolver = _resolver;
    }

    function resolveMarket(uint256 marketId, bytes32 outcome) external {
        require(msg.sender == resolver, "Only resolver");
        require(!resolved[marketId], "Already resolved");
        
        resolved[marketId] = true;
        winningOutcome[marketId] = outcome;
        
        emit MarketResolved(marketId, outcome);
    }
}
