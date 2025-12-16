// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DisputeBond {
    mapping(uint256 => address) public disputeCreator;
    mapping(uint256 => uint256) public bondAmount;
    
    event DisputeRaised(uint256 indexed marketId, address indexed discharger, uint256 bond);

    function raiseDispute(uint256 marketId) external payable {
        require(msg.value > 0, "Bond required");
        require(disputeCreator[marketId] == address(0), "Dispute active");
        
        disputeCreator[marketId] = msg.sender;
        bondAmount[marketId] = msg.value;
        
        emit DisputeRaised(marketId, msg.sender, msg.value);
    }
}
