"""
Batch backfill service for historical blockchain events
"""
import logging
import json
import os
from datetime import datetime
from typing import Optional
from django.conf import settings
from utils.contracts import get_contract_service
from .event_decoder import EventDecoder
from ..services import EventProcessor
from utils.logging import get_onchain_loggers

logger = logging.getLogger(__name__)


class BackfillService:
    """Service for backfilling historical blockchain events"""
    
    def __init__(self):
        self.contract_service = get_contract_service()
        self.decoder = EventDecoder()
        self.processor = EventProcessor()
        self.onchain_loggers = get_onchain_loggers()
    
    def backfill(
        self,
        from_block: int = 0,
        to_block: Optional[int] = None,
        batch_size: int = 1000
    ) -> Dict[str, Any]:
        """
        Backfill events from a block range
        
        Args:
            from_block: Starting block number
            to_block: Ending block number (None = latest)
            batch_size: Number of blocks per batch
        
        Returns:
            Summary statistics
        """
        if not self.contract_service.is_connected():
            raise ValueError("Web3 not connected")
        
        if to_block is None:
            to_block = self.contract_service.get_latest_block()
            if not to_block:
                raise ValueError("Could not get latest block")
        
        logger.info(f"Starting backfill from block {from_block} to {to_block}")
        
        start_time = datetime.now()
        total_events = 0
        total_processed = 0
        total_duplicates = 0
        total_errors = 0
        errors = []
        
        current_block = from_block
        
        try:
            while current_block <= to_block:
                batch_end = min(current_block + batch_size - 1, to_block)
                
                logger.info(f"Processing blocks {current_block} to {batch_end}")
                
                # Get events for this batch
                events = self.contract_service.get_events(
                    from_block=current_block,
                    to_block=batch_end
                )
                
                batch_processed = 0
                batch_duplicates = 0
                batch_errors = 0
                
                for event in events:
                    decoded = self.decoder.decode(event)
                    if decoded:
                        total_events += 1
                        result = self.processor.process_event(decoded)
                        
                        if result['success']:
                            batch_processed += 1
                            total_processed += 1
                        elif result.get('duplicate'):
                            batch_duplicates += 1
                            total_duplicates += 1
                        else:
                            batch_errors += 1
                            total_errors += 1
                            errors.append({
                                'tx_hash': decoded.get('transactionHash'),
                                'error': result.get('error'),
                                'event': decoded.get('event'),
                            })
                
                logger.info(
                    f"Batch complete: {batch_processed} processed, "
                    f"{batch_duplicates} duplicates, {batch_errors} errors"
                )
                
                current_block = batch_end + 1
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Generate log file
            log_data = {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration,
                'from_block': from_block,
                'to_block': to_block,
                'total_blocks': to_block - from_block + 1,
                'total_events_found': total_events,
                'total_events_processed': total_processed,
                'total_duplicates': total_duplicates,
                'total_errors': total_errors,
                'errors': errors[:100],  # Limit to first 100 errors
            }
            
            # Save log
            logs_dir = os.path.join(settings.BASE_DIR, 'LOGS', 'etl')
            os.makedirs(logs_dir, exist_ok=True)
            
            log_filename = f"backfill_{from_block}_{to_block}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            log_path = os.path.join(logs_dir, log_filename)
            
            with open(log_path, 'w') as f:
                json.dump(log_data, f, indent=2)
            
            logger.info(f"Backfill complete. Log saved to {log_path}")
            
            return log_data
            
        except KeyboardInterrupt:
            logger.warning("Backfill interrupted by user")
            raise
        except Exception as e:
            logger.error(f"Error in backfill: {e}", exc_info=True)
            raise

