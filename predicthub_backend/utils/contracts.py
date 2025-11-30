"""
Web3 contract interaction utilities for PredictHub
Production-grade contract service with async/sync support
"""
import json
import os
from typing import Optional, Dict, Any, List, Callable
from decimal import Decimal
from web3 import Web3, AsyncWeb3
from web3.types import TxReceipt, LogReceipt, Wei
try:
    from web3.middleware import ExtraDataToPOAMiddleware
except ImportError:
    # For web3.py v6+, use geth_poa_middleware instead
    try:
        from web3.middleware import geth_poa_middleware as ExtraDataToPOAMiddleware
    except ImportError:
        ExtraDataToPOAMiddleware = None
from web3.providers import HTTPProvider
try:
    from web3.providers import WebSocketProvider
except ImportError:
    # For web3.py v6+, it's WebsocketProvider (lowercase 's')
    from web3.providers import WebsocketProvider as WebSocketProvider
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class ContractService:
    """Service for interacting with the PredictionMarket smart contract"""
    
    def __init__(self):
        self.w3: Optional[Web3] = None
        self.w3_async: Optional[AsyncWeb3] = None
        self.contract = None
        self.contract_address: Optional[str] = None
        self.chain_id: int = 84532
        self.private_key: Optional[str] = None
        self.wallet_address: Optional[str] = None
        self._initialize_web3()
    
    def _initialize_web3(self):
        """Initialize Web3 connection and load contract"""
        http_provider_url = getattr(settings, 'WEB3_PROVIDER_HTTP', '')
        ws_provider_url = getattr(settings, 'WEB3_PROVIDER_WS', '')
        self.chain_id = getattr(settings, 'CHAIN_ID', 84532)
        contract_address = getattr(settings, 'CONTRACT_ADDRESS', '')
        self.private_key = getattr(settings, 'PRIVATE_KEY', '')
        self.wallet_address = getattr(settings, 'WALLET_ADDRESS', '')
        
        if not http_provider_url:
            logger.warning("WEB3_PROVIDER_HTTP not set, contract service unavailable")
            return
        
        try:
            # Initialize HTTP provider (sync)
            provider = HTTPProvider(http_provider_url)
            self.w3 = Web3(provider)
            
            # Auto-detect Base POA compatibility (Base Sepolia uses POA)
            if self.chain_id in [84532, 84531]:  # Base Sepolia or Base Goerli
                try:
                    if ExtraDataToPOAMiddleware:
                        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
                        logger.info("POA middleware injected for Base network")
                    else:
                        # Try geth_poa_middleware for web3.py v6+
                        from web3.middleware import geth_poa_middleware
                        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                        logger.info("POA middleware (geth_poa_middleware) injected for Base network")
                except Exception as e:
                    logger.warning(f"Could not inject POA middleware: {e}")
            
            if not self.w3.is_connected():
                logger.error("Failed to connect to Web3 HTTP provider")
                return
            
            # Initialize WebSocket provider (async) if available
            if ws_provider_url:
                try:
                    ws_provider = WebSocketProvider(ws_provider_url)
                    self.w3_async = AsyncWeb3(ws_provider)
                    logger.info("WebSocket provider initialized")
                except Exception as e:
                    logger.warning(f"Could not initialize WebSocket provider: {e}")
            
            # Load contract - try contract.json first, then fallback to ABI path
            abi = None
            contract_json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'utils', 'abis', 'contract.json')
            
            # Try loading from contract.json (has address + ABI)
            if os.path.exists(contract_json_path):
                try:
                    with open(contract_json_path, 'r') as f:
                        contract_data = json.load(f)
                        abi = contract_data.get('abi', [])
                        # Use address from contract.json if CONTRACT_ADDRESS not set
                        if not contract_address and contract_data.get('address'):
                            contract_address = contract_data.get('address')
                            logger.info(f"Using contract address from contract.json: {contract_address}")
                except Exception as e:
                    logger.warning(f"Error loading contract.json: {e}")
            
            # Fallback to CONTRACT_ABI_PATH
            if not abi:
                abi_path = getattr(settings, 'CONTRACT_ABI_PATH', '')
                if abi_path and os.path.exists(abi_path):
                    try:
                        with open(abi_path, 'r') as f:
                            abi_data = json.load(f)
                            # Handle both raw ABI array and contract.json format
                            if isinstance(abi_data, list):
                                abi = abi_data
                            elif isinstance(abi_data, dict) and 'abi' in abi_data:
                                abi = abi_data['abi']
                                if not contract_address and abi_data.get('address'):
                                    contract_address = abi_data.get('address')
                            else:
                                abi = abi_data
                    except Exception as e:
                        logger.warning(f"Error loading ABI from {abi_path}: {e}")
            
            if not abi:
                logger.warning("ABI not found in contract.json or CONTRACT_ABI_PATH")
                return
            
            if not contract_address:
                logger.warning("CONTRACT_ADDRESS not set and not found in contract.json")
                return
            
            self.contract_address = contract_address
            self.contract = self.w3.eth.contract(address=contract_address, abi=abi)
            
            logger.info(f"Contract service initialized: {contract_address} on chain {self.chain_id}")
            
        except Exception as e:
            logger.error(f"Error initializing Web3: {e}", exc_info=True)
    
    def is_connected(self) -> bool:
        """Check if Web3 is connected"""
        return self.w3 is not None and self.w3.is_connected()
    
    def get_contract(self):
        """Get the contract instance"""
        return self.contract
    
    def get_latest_block(self) -> Optional[int]:
        """Get the latest block number"""
        if not self.is_connected():
            return None
        try:
            return self.w3.eth.block_number
        except Exception as e:
            logger.error(f"Error getting latest block: {e}")
            return None
    
    def call(self, function_name: str, *args, **kwargs) -> Any:
        """
        Call a contract function (read-only)
        
        Args:
            function_name: Name of the contract function
            *args: Positional arguments for the function
            **kwargs: Keyword arguments (e.g., block_identifier)
        
        Returns:
            Function return value
        """
        if not self.contract:
            raise ValueError("Contract not initialized")
        
        try:
            func = getattr(self.contract.functions, function_name)
            result = func(*args).call(**kwargs)
            return result
        except Exception as e:
            logger.error(f"Error calling {function_name}: {e}")
            raise
    
    def send_tx(self, function_name: str, *args, value: Wei = 0, gas_limit: Optional[int] = None) -> str:
        """
        Send a transaction to the contract
        
        Args:
            function_name: Name of the contract function
            *args: Positional arguments for the function
            value: ETH value to send (in Wei)
            gas_limit: Optional gas limit
        
        Returns:
            Transaction hash
        """
        if not self.contract:
            raise ValueError("Contract not initialized")
        
        if not self.private_key or not self.wallet_address:
            raise ValueError("PRIVATE_KEY and WALLET_ADDRESS must be set to send transactions")
        
        try:
            # Get function
            func = getattr(self.contract.functions, function_name)
            
            # Build transaction
            tx = func(*args).build_transaction({
                'from': self.wallet_address,
                'nonce': self.w3.eth.get_transaction_count(self.wallet_address),
                'chainId': self.chain_id,
                'value': value,
            })
            
            if gas_limit:
                tx['gas'] = gas_limit
            else:
                # Estimate gas
                tx['gas'] = self.w3.eth.estimate_gas(tx)
            
            # Sign transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            logger.info(f"Transaction sent: {tx_hash.hex()}")
            return tx_hash.hex()
            
        except Exception as e:
            logger.error(f"Error sending transaction {function_name}: {e}")
            raise
    
    def get_events(
        self,
        from_block: int = 0,
        to_block: Optional[int] = None,
        event_name: Optional[str] = None,
    ) -> List[LogReceipt]:
        """
        Get events from the contract
        
        Args:
            from_block: Starting block number
            to_block: Ending block number (None = latest)
            event_name: Specific event name (None = all events)
        
        Returns:
            List of event logs
        """
        if not self.contract:
            return []
        
        if to_block is None:
            to_block = 'latest'
        
        try:
            if event_name:
                event = getattr(self.contract.events, event_name, None)
                if not event:
                    logger.warning(f"Event {event_name} not found")
                    return []
                events = event.get_logs(fromBlock=from_block, toBlock=to_block)
            else:
                # Get all events
                events = []
                event_names = ['MarketCreated', 'TradeExecuted', 'LiquidityAdded', 'MarketResolved']
                for evt_name in event_names:
                    event = getattr(self.contract.events, evt_name, None)
                    if event:
                        try:
                            events.extend(event.get_logs(fromBlock=from_block, toBlock=to_block))
                        except Exception as e:
                            logger.warning(f"Error getting {evt_name} events: {e}")
            
            return events
        except Exception as e:
            logger.error(f"Error getting events: {e}")
            return []
    
    async def subscribe_to_events(
        self,
        event_name: str,
        callback: Callable[[Dict[str, Any]], None],
        from_block: Optional[int] = None
    ):
        """
        Subscribe to contract events via WebSocket
        
        Args:
            event_name: Event name to subscribe to
            callback: Async callback function to handle events
            from_block: Starting block (None = latest)
        """
        if not self.w3_async or not self.contract:
            raise ValueError("WebSocket provider or contract not initialized")
        
        try:
            event = getattr(self.contract.events, event_name, None)
            if not event:
                raise ValueError(f"Event {event_name} not found")
            
            # Create filter
            if from_block:
                event_filter = await event.create_filter(fromBlock=from_block)
            else:
                event_filter = await event.create_filter()
            
            # Listen for new events
            async for event_log in event_filter.get_new_entries():
                decoded = event().process_log(event_log)
                await callback({
                    'event': decoded.event,
                    'args': dict(decoded.args),
                    'address': decoded.address,
                    'blockNumber': decoded.blockNumber,
                    'transactionHash': decoded.transactionHash.hex(),
                    'logIndex': decoded.logIndex,
                })
                
        except Exception as e:
            logger.error(f"Error subscribing to {event_name}: {e}")
            raise
    
    def decode_event(self, log: LogReceipt) -> Optional[Dict[str, Any]]:
        """Decode an event log"""
        if not self.contract:
            return None
        
        event_names = ['MarketCreated', 'TradeExecuted', 'LiquidityAdded', 'MarketResolved']
        for event_name in event_names:
            try:
                event = getattr(self.contract.events, event_name)
                decoded = event().process_log(log)
                return {
                    'event': decoded.event,
                    'args': dict(decoded.args),
                    'address': decoded.address,
                    'blockNumber': decoded.blockNumber,
                    'transactionHash': decoded.transactionHash.hex(),
                    'logIndex': decoded.logIndex,
                }
            except Exception:
                continue
        
        logger.warning(f"Could not decode event log: {log.get('topics', [])}")
        return None
    
    def wait_for_tx(self, tx_hash: str, timeout: int = 300) -> Optional[TxReceipt]:
        """
        Wait for transaction receipt
        
        Args:
            tx_hash: Transaction hash
            timeout: Timeout in seconds
        
        Returns:
            Transaction receipt or None
        """
        if not self.is_connected():
            return None
        
        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
            return receipt
        except Exception as e:
            logger.error(f"Error waiting for transaction {tx_hash}: {e}")
            return None


# Singleton instance
_contract_service = None


def get_contract_service() -> ContractService:
    """Get the singleton contract service instance"""
    global _contract_service
    if _contract_service is None:
        _contract_service = ContractService()
    return _contract_service
