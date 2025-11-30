"""
WebSocket listener for real-time blockchain events
"""
import asyncio
import logging
from typing import Callable, Optional
from utils.contracts import get_contract_service
from .event_decoder import EventDecoder
from ..services import EventProcessor

logger = logging.getLogger(__name__)


class EventListener:
    """Listens to blockchain events via WebSocket"""
    
    def __init__(self):
        self.contract_service = get_contract_service()
        self.decoder = EventDecoder()
        self.processor = EventProcessor()
        self.running = False
    
    async def start(self, from_block: Optional[int] = None):
        """
        Start listening to events
        
        Args:
            from_block: Starting block number (None = latest)
        """
        if not hasattr(self.contract_service, 'w3_async') or not self.contract_service.w3_async:
            logger.error("WebSocket provider not available")
            raise ValueError("WEB3_PROVIDER_WS must be set for WebSocket listener")
        
        self.running = True
        logger.info("Starting WebSocket event listener")
        
        # Subscribe to all events
        event_names = ['UserCreated', 'MarketCreated', 'TradeExecuted', 'TransactionCreated', 'LiquidityAdded', 'MarketResolved']
        
        async def handle_event(event_data):
            """Handle incoming event"""
            if not self.running:
                return
            
            try:
                result = self.processor.process_event(event_data)
                if result['success']:
                    logger.info(f"Processed {event_data.get('event', 'unknown')} via WebSocket")
                elif result.get('duplicate'):
                    logger.debug(f"Duplicate event suppressed: {event_data.get('event', 'unknown')}")
                else:
                    logger.error(f"Error processing event: {result.get('error')}")
            except Exception as e:
                logger.error(f"Error handling event: {e}", exc_info=True)
        
        # Create subscription tasks
        tasks = []
        for event_name in event_names:
            try:
                if hasattr(self.contract_service, 'subscribe_to_events'):
                    task = asyncio.create_task(
                        self.contract_service.subscribe_to_events(event_name, handle_event, from_block)
                    )
                    tasks.append(task)
                    logger.info(f"Subscribed to {event_name} events")
                else:
                    logger.warning(f"Contract service does not support subscribe_to_events")
            except Exception as e:
                logger.error(f"Error subscribing to {event_name}: {e}")
        
        # Wait for all subscriptions
        try:
            if tasks:
                await asyncio.gather(*tasks)
            else:
                logger.warning("No event subscriptions created")
        except asyncio.CancelledError:
            logger.info("Event listener cancelled")
        except Exception as e:
            logger.error(f"Error in event listener: {e}", exc_info=True)
    
    def stop(self):
        """Stop the listener"""
        self.running = False
        logger.info("Stopping WebSocket event listener")

