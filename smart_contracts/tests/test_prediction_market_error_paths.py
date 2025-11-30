"""
Brownie Tests - Error/Failure Paths Coverage

This file specifically tests error scenarios, revert cases, permission denial, and edge conditions.

Requirements:
- ≥10 tests covering failure/error paths
- Revert cases
- Permission denial
- Edge conditions
"""

from brownie import PredictionMarket, accounts, reverts, chain
import pytest


@pytest.fixture(scope="function")
def prediction_market():
    """Deploy fresh contract for each test"""
    return PredictionMarket.deploy({'from': accounts[0]})


@pytest.fixture(scope="function")
def owner():
    return accounts[0]


@pytest.fixture(scope="function")
def user1():
    return accounts[1]


@pytest.fixture(scope="function")
def user2():
    return accounts[2]


# ============================================================================
# REVERT CASES - Input Validation Errors
# ============================================================================

def test_revert_market_creation_empty_title(prediction_market, user1):
    """
    ERROR PATH: Revert when creating market with empty title
    Tests: require() validation, revert with message
    """
    end_time = chain.time() + 86400
    
    with reverts("Title cannot be empty"):
        prediction_market.createMarket("", end_time, {'from': user1})


def test_revert_market_creation_past_end_time(prediction_market, user1):
    """
    ERROR PATH: Revert when end time is in the past
    Tests: Time validation, revert with message
    """
    past_time = chain.time() - 86400
    
    with reverts("End time must be in the future"):
        prediction_market.createMarket("Test Market", past_time, {'from': user1})


def test_revert_trade_zero_amount(prediction_market, user1, user2):
    """
    ERROR PATH: Revert when placing trade with zero amount
    Tests: Amount validation, revert with message
    """
    end_time = chain.time() + 86400
    prediction_market.createMarket("Test Market", end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    
    with reverts("Amount must be greater than 0"):
        prediction_market.placeTrade(market_id, True, 0, {'from': user2})


def test_revert_liquidity_zero_amount(prediction_market, user1, user2):
    """
    ERROR PATH: Revert when adding liquidity with zero amount
    Tests: Amount validation, revert with message
    """
    end_time = chain.time() + 86400
    prediction_market.createMarket("Test Market", end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    
    with reverts("Amount must be greater than 0"):
        prediction_market.addLiquidity(market_id, 0, {'from': user2})


def test_revert_trade_invalid_market_id(prediction_market, user2):
    """
    ERROR PATH: Revert when trading on non-existent market
    Tests: Market existence validation, revert with message
    """
    invalid_market_id = 99999
    
    with reverts("Invalid market"):
        prediction_market.placeTrade(invalid_market_id, True, "1 ether", {'from': user2})


def test_revert_liquidity_invalid_market_id(prediction_market, user2):
    """
    ERROR PATH: Revert when adding liquidity to non-existent market
    Tests: Market existence validation, revert with message
    """
    invalid_market_id = 99999
    
    with reverts("Invalid market"):
        prediction_market.addLiquidity(invalid_market_id, "1 ether", {'from': user2})


# ============================================================================
# REVERT CASES - State-Based Errors
# ============================================================================

def test_revert_trade_market_ended(prediction_market, user1, user2):
    """
    ERROR PATH: Revert when trading on ended market
    Tests: Market state validation (end time check), revert with message
    """
    # Create market with short end time
    short_end_time = chain.time() + 3600  # 1 hour
    prediction_market.createMarket("Short Market", short_end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    
    # Advance time past end time
    chain.sleep(7200)  # 2 hours
    chain.mine()
    
    with reverts("Market ended"):
        prediction_market.placeTrade(market_id, True, "1 ether", {'from': user2})


def test_revert_trade_market_resolved(prediction_market, owner, user1, user2):
    """
    ERROR PATH: Revert when trading on resolved market
    Tests: Market resolution state check, revert with message
    """
    end_time = chain.time() + 86400
    prediction_market.createMarket("Test Market", end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    
    # Resolve the market
    chain.sleep(86400)
    chain.mine()
    prediction_market.resolveMarket(market_id, True, {'from': owner})
    
    with reverts("Market already resolved"):
        prediction_market.placeTrade(market_id, True, "1 ether", {'from': user2})


def test_revert_liquidity_market_resolved(prediction_market, owner, user1, user2):
    """
    ERROR PATH: Revert when adding liquidity to resolved market
    Tests: Market resolution state check, revert with message
    """
    end_time = chain.time() + 86400
    prediction_market.createMarket("Test Market", end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    
    # Resolve the market
    chain.sleep(86400)
    chain.mine()
    prediction_market.resolveMarket(market_id, True, {'from': owner})
    
    with reverts("Market already resolved"):
        prediction_market.addLiquidity(market_id, "1 ether", {'from': user2})


# ============================================================================
# PERMISSION DENIAL - Access Control Errors
# ============================================================================

def test_revert_resolve_market_not_owner(prediction_market, user1, user2):
    """
    ERROR PATH: Revert when non-owner tries to resolve market
    Tests: Owner-only access control, revert with message
    """
    end_time = chain.time() + 86400
    prediction_market.createMarket("Test Market", end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    
    # Advance time
    chain.sleep(86400)
    chain.mine()
    
    # Non-owner tries to resolve
    with reverts("Not owner"):
        prediction_market.resolveMarket(market_id, True, {'from': user2})


def test_revert_resolve_market_not_ended(prediction_market, owner, user1):
    """
    ERROR PATH: Revert when trying to resolve market before end time
    Tests: Time-based state validation, revert with message
    """
    end_time = chain.time() + 86400
    prediction_market.createMarket("Test Market", end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    
    # Try to resolve before end time (should fail)
    with reverts("Market has not ended yet"):
        prediction_market.resolveMarket(market_id, True, {'from': owner})


def test_revert_resolve_market_already_resolved(prediction_market, owner, user1):
    """
    ERROR PATH: Revert when trying to resolve already resolved market
    Tests: State duplication prevention, revert with message
    """
    end_time = chain.time() + 86400
    prediction_market.createMarket("Test Market", end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    
    # Resolve once
    chain.sleep(86400)
    chain.mine()
    prediction_market.resolveMarket(market_id, True, {'from': owner})
    
    # Try to resolve again (should fail)
    with reverts("Market already resolved"):
        prediction_market.resolveMarket(market_id, False, {'from': owner})


# ============================================================================
# EDGE CONDITIONS - Boundary Cases
# ============================================================================

def test_revert_market_id_zero(prediction_market, user2):
    """
    EDGE CASE: Revert when using market ID 0 (invalid)
    Tests: Zero value validation, boundary condition
    """
    with reverts("Invalid market"):
        prediction_market.placeTrade(0, True, "1 ether", {'from': user2})


def test_revert_market_id_max_uint(prediction_market, user2):
    """
    EDGE CASE: Revert when using extremely large market ID
    Tests: Upper boundary validation, non-existent market
    """
    max_uint = 2**256 - 1
    
    with reverts("Invalid market"):
        prediction_market.placeTrade(max_uint, True, "1 ether", {'from': user2})


def test_revert_trade_after_exact_end_time(prediction_market, user1, user2):
    """
    EDGE CASE: Revert when trading exactly at end time
    Tests: Time boundary condition (end time inclusive)
    """
    end_time = chain.time() + 3600
    prediction_market.createMarket("Test Market", end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    
    # Advance to exactly end time
    chain.sleep(3600)
    chain.mine()
    
    # Should fail because market has ended
    with reverts("Market ended"):
        prediction_market.placeTrade(market_id, True, "1 ether", {'from': user2})


def test_revert_resolve_before_exact_end_time(prediction_market, owner, user1):
    """
    EDGE CASE: Revert when resolving 1 second before end time
    Tests: Time boundary condition (must be past end time)
    """
    end_time = chain.time() + 3600
    prediction_market.createMarket("Test Market", end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    
    # Advance to 1 second before end time
    chain.sleep(3599)
    chain.mine()
    
    # Should fail - not past end time yet
    with reverts("Market has not ended yet"):
        prediction_market.resolveMarket(market_id, True, {'from': owner})


def test_revert_multiple_operations_on_resolved_market(prediction_market, owner, user1, user2):
    """
    EDGE CASE: Multiple operations fail on resolved market
    Tests: State consistency across multiple operations
    """
    end_time = chain.time() + 86400
    prediction_market.createMarket("Test Market", end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    
    # Resolve market
    chain.sleep(86400)
    chain.mine()
    prediction_market.resolveMarket(market_id, True, {'from': owner})
    
    # All operations should fail on resolved market
    with reverts("Market already resolved"):
        prediction_market.placeTrade(market_id, True, "1 ether", {'from': user2})
    
    with reverts("Market already resolved"):
        prediction_market.addLiquidity(market_id, "1 ether", {'from': user2})


def test_revert_sequential_errors(prediction_market, user1, user2):
    """
    EDGE CASE: Sequential error conditions
    Tests: Error handling in sequence of operations
    """
    # First error: Invalid market ID
    with reverts("Invalid market"):
        prediction_market.placeTrade(999, True, "1 ether", {'from': user2})
    
    # Create market
    end_time = chain.time() + 86400
    prediction_market.createMarket("Test Market", end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    
    # Second error: Zero amount
    with reverts("Amount must be greater than 0"):
        prediction_market.placeTrade(market_id, True, 0, {'from': user2})


# ============================================================================
# SUMMARY
# ============================================================================
"""
Total Error/Failure Tests: 18

REVERT CASES (Input Validation): 6 tests
- Empty title
- Past end time
- Zero amount (trade)
- Zero amount (liquidity)
- Invalid market ID (trade)
- Invalid market ID (liquidity)

REVERT CASES (State-Based): 3 tests
- Market ended
- Market resolved (trade)
- Market resolved (liquidity)

PERMISSION DENIAL: 3 tests
- Not owner (resolve)
- Not ended (resolve)
- Already resolved (resolve)

EDGE CONDITIONS: 6 tests
- Market ID zero
- Market ID max uint
- Exact end time
- 1 second before end time
- Multiple operations on resolved market
- Sequential errors

All tests use reverts() to verify error messages and ensure proper error handling.
"""

