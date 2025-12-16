// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IOutcomeToken {
    function mint(address to, uint256 id, uint256 amount) external;
    function burn(address from, uint256 id, uint256 amount) external;
}

contract OutcomeToken is IOutcomeToken {
    mapping(uint256 => mapping(address => uint256)) public balanceOf;
    mapping(uint256 => uint256) public totalSupply;
    address public amm;

    modifier onlyAMM() {
        require(msg.sender == amm, "Only AMM can mint/burn");
        _;
    }

    constructor(address _amm) {
        amm = _amm;
    }

    function setAMM(address _amm) external {
        require(amm == address(0), "AMM already set");
        amm = _amm;
    }

    function mint(address to, uint256 id, uint256 amount) external override onlyAMM {
        balanceOf[id][to] += amount;
        totalSupply[id] += amount;
    }

    function burn(address from, uint256 id, uint256 amount) external override onlyAMM {
        require(balanceOf[id][from] >= amount, "Insufficient balance");
        balanceOf[id][from] -= amount;
        totalSupply[id] -= amount;
    }
}
