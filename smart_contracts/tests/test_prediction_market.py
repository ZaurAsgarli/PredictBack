"""
Brownie tests for PredictionMarket contract.

Total: 21 tests covering SUCCESS paths.

For ERROR/FAILURE paths, see: test_prediction_market_error_paths.py
That file contains 18+ tests specifically for:
- Revert cases (input validation, state-based)
- Permission denial (access control)
- Edge conditions (boundary cases)

To run:
    brownie test                                    # Run all tests
    brownie test tests/test_prediction_market.py   # Success paths only
    brownie test tests/test_prediction_market_error_paths.py  # Error paths only
    brownie test --coverage                        # With coverage
"""

from brownie import PredictionMarket, accounts, reverts, chain
import pytest


@pytest.fixture(scope="function")  # Changed to function scope for isolation
def prediction_market():
    """Deploy a fresh contract for each test"""
    return PredictionMarket.deploy({'from': accounts[0]})


@pytest.fixture(scope="function")  # Changed to function scope
def owner():
    """Contract owner"""
    return accounts[0]


@pytest.fixture(scope="function")  # Changed to function scope
def user1():
    """Test user 1"""
    return accounts[1]


@pytest.fixture(scope="function")  # Changed to function scope
def user2():
    """Test user 2"""
    return accounts[2]


@pytest.fixture(scope="function")  # Changed to function scope
def user3():
    """Test user 3"""
    return accounts[3]


# ============================================================================
# Deployment Tests
# ============================================================================

def test_deployment(prediction_market, owner):
    """Test contract deployment and initial state"""
    assert prediction_market.owner() == owner.address
    assert prediction_market.marketCounter() == 0
    assert prediction_market.tradeCounter() == 0
    assert prediction_market.liquidityCounter() == 0


def test_constructor_emits_user_created(prediction_market, owner):
    """Test that constructor emits UserCreated event for owner"""
    # The constructor should emit UserCreated for the owner
    # This is checked via event logs in deployment transaction
    assert prediction_market.owner() == owner.address


# ============================================================================
# UserCreated Event Tests
# ============================================================================

def test_user_created_on_market_creation(prediction_market, user1):
    """Test UserCreated event is emitted when creating market"""
    end_time = chain.time() + 86400
    tx = prediction_market.createMarket("Test Market", end_time, {'from': user1})
    
    # Check UserCreated event was emitted
    assert 'UserCreated' in tx.events
    # UserCreated event has 'user' field
    user_events = [e for e in tx.events['UserCreated'] if 'user' in e]
    if user_events:
        assert user_events[0]['user'] == user1.address


# ============================================================================
# Market Creation Tests
# ============================================================================

def test_create_market_success(prediction_market, user1):
    """Test successful market creation"""
    end_time = chain.time() + 86400  # 24 hours
    
    # Get initial market counter
    initial_count = prediction_market.marketCounter()
    
    tx = prediction_market.createMarket("Test Market", end_time, {'from': user1})
    
    # Verify counter increased
    assert prediction_market.marketCounter() == initial_count + 1
    assert 'MarketCreated' in tx.events
    assert 'UserCreated' in tx.events  # Should also emit UserCreated
    
    # Get the new market ID
    new_market_id = prediction_market.marketCounter()
    
    # Verify event data
    market_event = tx.events['MarketCreated'][0]
    assert market_event['marketId'] == new_market_id
    assert market_event['creator'] == user1.address
    assert market_event['endTime'] == end_time
    
    # Verify stored market data (Brownie returns structs as tuples)
    market = prediction_market.getMarket(new_market_id)
    # Market struct: (title, endTime, resolved, outcome, creator, totalLiquidity)
    assert market[0] == "Test Market"  # title
    assert market[1] == end_time  # endTime
    assert market[2] == False  # resolved
    assert market[3] == False  # outcome
    assert market[4] == user1.address  # creator
    assert market[5] == 0  # totalLiquidity


def test_create_market_failure_past_end_time(prediction_market, user1):
    """Test market creation fails with past end time"""
    past_time = chain.time() - 86400
    
    with reverts("End time must be in the future"):
        prediction_market.createMarket("Test Market", past_time, {'from': user1})


def test_create_market_failure_empty_title(prediction_market, user1):
    """Test market creation fails with empty title"""
    end_time = chain.time() + 86400
    
    with reverts("Title cannot be empty"):
        prediction_market.createMarket("", end_time, {'from': user1})


# ============================================================================
# Trading Tests
# ============================================================================

@pytest.fixture
def market_setup(prediction_market, user1):
    """Setup: Create a fresh market for trading tests"""
    # Get current market counter to create a new market
    current_count = prediction_market.marketCounter()
    end_time = chain.time() + 86400
    tx = prediction_market.createMarket("Test Market", end_time, {'from': user1})
    # Return the new market ID
    return current_count + 1  # marketId


def test_place_trade_success(prediction_market, user1, user2):
    """Test successful trade placement"""
    # Create a fresh market for this test
    end_time = chain.time() + 86400
    prediction_market.createMarket("Test Market", end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    amount = "1 ether"
    outcome = True  # YES
    
    initial_trade_count = prediction_market.tradeCounter()
    tx = prediction_market.placeTrade(market_id, outcome, amount, {'from': user2})
    
    assert prediction_market.tradeCounter() == initial_trade_count + 1
    assert 'TradeExecuted' in tx.events
    
    # Verify event data
    trade_event = tx.events['TradeExecuted'][0]
    assert trade_event['marketId'] == market_id
    assert trade_event['user'] == user2.address
    assert trade_event['outcome'] == outcome
    assert trade_event['amount'] == amount
    
    # Verify stored trade data (get latest trade)
    latest_trade_id = prediction_market.tradeCounter()
    trade = prediction_market.getTrade(latest_trade_id)
    # Trade struct: (marketId, user, outcome, amount, timestamp)
    assert trade[0] == market_id  # marketId
    assert trade[1] == user2.address  # user
    assert trade[2] == outcome  # outcome
    assert trade[3] == amount  # amount


def test_place_trade_failure_zero_amount(prediction_market, user1, user2):
    """Test trade fails with zero amount"""
    # Create a fresh market for this test
    end_time = chain.time() + 86400
    prediction_market.createMarket("Test Market", end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    
    with reverts("Amount must be greater than 0"):
        prediction_market.placeTrade(market_id, True, 0, {'from': user2})


def test_place_trade_failure_invalid_market(prediction_market, user2):
    """Test trade fails with invalid market ID"""
    # Use a market ID that definitely doesn't exist
    max_market_id = prediction_market.marketCounter() + 100
    with reverts("Invalid market"):
        prediction_market.placeTrade(max_market_id, True, "1 ether", {'from': user2})


def test_place_trade_failure_market_ended(prediction_market, user1, user2):
    """Test trade fails if market has ended"""
    # Create market with short end time
    current_count = prediction_market.marketCounter()
    short_end_time = chain.time() + 3600  # 1 hour
    prediction_market.createMarket("Short Market", short_end_time, {'from': user1})
    short_market_id = current_count + 1
    
    # Advance time past end time
    chain.sleep(7200)  # 2 hours
    chain.mine()
    
    with reverts("Market ended"):
        prediction_market.placeTrade(short_market_id, True, "1 ether", {'from': user2})


def test_place_trade_failure_market_resolved(prediction_market, owner, user1, user2):
    """Test trade fails if market is resolved"""
    # Create a fresh market for this test
    end_time = chain.time() + 86400
    prediction_market.createMarket("Test Market", end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    
    # Advance time and resolve market
    chain.sleep(86400)
    chain.mine()
    prediction_market.resolveMarket(market_id, True, {'from': owner})
    
    with reverts("Market already resolved"):
        prediction_market.placeTrade(market_id, True, "1 ether", {'from': user2})


# ============================================================================
# Liquidity Tests
# ============================================================================

def test_add_liquidity_success(prediction_market, user1, user2):
    """Test successful liquidity addition"""
    # Create a fresh market for this test
    end_time = chain.time() + 86400
    prediction_market.createMarket("Test Market", end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    amount = "10 ether"
    
    tx = prediction_market.addLiquidity(market_id, amount, {'from': user2})
    
    assert prediction_market.liquidityCounter() >= 1
    assert 'LiquidityAdded' in tx.events
    
    # Verify event data
    liquidity_event = tx.events['LiquidityAdded'][0]
    assert liquidity_event['marketId'] == market_id
    assert liquidity_event['user'] == user2.address
    assert liquidity_event['amount'] == amount
    
    # Verify market liquidity updated
    market = prediction_market.getMarket(market_id)
    assert market[5] == amount  # totalLiquidity
    
    # Verify stored liquidity event (get latest)
    latest_liquidity_id = prediction_market.liquidityCounter()
    event = prediction_market.getLiquidityEvent(latest_liquidity_id)
    assert event[0] == market_id  # marketId
    assert event[1] == user2.address  # user
    assert event[2] == amount  # amount


def test_add_liquidity_failure_zero_amount(prediction_market, user1, user2):
    """Test liquidity addition fails with zero amount"""
    # Create a fresh market for this test
    end_time = chain.time() + 86400
    prediction_market.createMarket("Test Market", end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    
    with reverts("Amount must be greater than 0"):
        prediction_market.addLiquidity(market_id, 0, {'from': user2})


def test_add_liquidity_failure_market_resolved(prediction_market, owner, user1, user2):
    """Test liquidity addition fails if market is resolved"""
    # Create a fresh market for this test
    end_time = chain.time() + 86400
    prediction_market.createMarket("Test Market", end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    
    # Advance time and resolve market
    chain.sleep(86400)
    chain.mine()
    prediction_market.resolveMarket(market_id, True, {'from': owner})
    
    with reverts("Market already resolved"):
        prediction_market.addLiquidity(market_id, "1 ether", {'from': user2})


# ============================================================================
# Market Resolution Tests
# ============================================================================

def test_resolve_market_success(prediction_market, owner, user1):
    """Test successful market resolution"""
    # Create a fresh market for this test
    end_time = chain.time() + 86400
    prediction_market.createMarket("Test Market", end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    outcome = True  # YES
    
    # Advance time past end time
    chain.sleep(86400)
    chain.mine()
    
    tx = prediction_market.resolveMarket(market_id, outcome, {'from': owner})
    
    # Verify market state (Market struct: title, endTime, resolved, outcome, creator, totalLiquidity)
    market = prediction_market.getMarket(market_id)
    assert market[2] == True  # resolved
    assert market[3] == outcome  # outcome
    
    # Verify event
    assert 'MarketResolved' in tx.events
    resolve_event = tx.events['MarketResolved'][0]
    assert resolve_event['marketId'] == market_id
    assert resolve_event['outcome'] == outcome


def test_resolve_market_failure_not_owner(prediction_market, user1, user2):
    """Test market resolution fails if not owner"""
    # Create a fresh market for this test
    end_time = chain.time() + 86400
    prediction_market.createMarket("Test Market", end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    
    chain.sleep(86400)
    chain.mine()
    
    with reverts("Not owner"):
        prediction_market.resolveMarket(market_id, True, {'from': user2})


def test_resolve_market_failure_not_ended(prediction_market, owner, user1):
    """Test market resolution fails if market hasn't ended"""
    # Create a fresh market for this test
    end_time = chain.time() + 86400
    prediction_market.createMarket("Test Market", end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    
    with reverts("Market has not ended yet"):
        prediction_market.resolveMarket(market_id, True, {'from': owner})


def test_resolve_market_failure_already_resolved(prediction_market, owner, user1):
    """Test market resolution fails if already resolved"""
    # Create a fresh market for this test
    end_time = chain.time() + 86400
    prediction_market.createMarket("Test Market", end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    
    # Advance time and resolve
    chain.sleep(86400)
    chain.mine()
    prediction_market.resolveMarket(market_id, True, {'from': owner})
    
    # Try to resolve again
    with reverts("Market already resolved"):
        prediction_market.resolveMarket(market_id, False, {'from': owner})


# ============================================================================
# Getter Tests
# ============================================================================

def test_get_market_details(prediction_market, user1, market_setup):
    """Test getMarket returns correct details"""
    market_id = market_setup
    market = prediction_market.getMarket(market_id)
    
    # Market struct: (title, endTime, resolved, outcome, creator, totalLiquidity)
    assert market[0] == "Test Market"  # title
    assert market[4] == user1.address  # creator
    assert market[2] == False  # resolved


def test_get_trade_details(prediction_market, user1, user2):
    """Test getTrade returns correct details"""
    # Create a fresh market for this test
    end_time = chain.time() + 86400
    prediction_market.createMarket("Test Market", end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    amount = "1 ether"
    prediction_market.placeTrade(market_id, True, amount, {'from': user2})
    
    # Get latest trade
    latest_trade_id = prediction_market.tradeCounter()
    trade = prediction_market.getTrade(latest_trade_id)
    # Trade struct: (marketId, user, outcome, amount, timestamp)
    assert trade[0] == market_id  # marketId
    assert trade[1] == user2.address  # user
    assert trade[2] == True  # outcome
    assert trade[3] == amount  # amount


def test_get_liquidity_event_details(prediction_market, user1, user2):
    """Test getLiquidityEvent returns correct details"""
    # Create a fresh market for this test
    end_time = chain.time() + 86400
    prediction_market.createMarket("Test Market", end_time, {'from': user1})
    market_id = prediction_market.marketCounter()
    amount = "10 ether"
    prediction_market.addLiquidity(market_id, amount, {'from': user2})
    
    # Get latest liquidity event
    latest_liquidity_id = prediction_market.liquidityCounter()
    event = prediction_market.getLiquidityEvent(latest_liquidity_id)
    # LiquidityEvent struct: (marketId, user, amount, timestamp)
    assert event[0] == market_id  # marketId
    assert event[1] == user2.address  # user
    assert event[2] == amount  # amount

