"""
Event decoder for contract events
"""
import logging
from typing import Dict, Any, Optional
from web3.types import LogReceipt
from backend_api.core.utils.contracts import get_contract_service

logger = logging.getLogger(__name__)


class EventDecoder:
    """Decodes blockchain event logs to structured data"""
    
    def __init__(self):
        self.contract_service = get_contract_service()
    
    def decode(self, log: LogReceipt) -> Optional[Dict[str, Any]]:
        """
        Decode a raw event log
        
        Args:
            log: Raw event log from Web3
        
        Returns:
            Decoded event data or None if decoding fails
        """
        if not self.contract_service.contract:
            logger.warning("Contract not initialized, cannot decode events")
            return None
        
        return self.contract_service.decode_event(log)
    
    def decode_batch(self, logs: list[LogReceipt]) -> list[Dict[str, Any]]:
        """
        Decode multiple event logs
        
        Args:
            logs: List of raw event logs
        
        Returns:
            List of decoded event data
        """
        decoded = []
        for log in logs:
            result = self.decode(log)
            if result:
                decoded.append(result)
        return decoded

