"""
Structured JSON logging utilities for on-chain events
Supports SOC/SIEM/SOAR engineering, process intelligence, and monitoring
"""
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Formatter that outputs structured JSON logs"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, 'event_name'):
            log_data['event_name'] = record.event_name
        if hasattr(record, 'tx_hash'):
            log_data['tx_hash'] = record.tx_hash
        if hasattr(record, 'block_number'):
            log_data['block_number'] = record.block_number
        if hasattr(record, 'market_id'):
            log_data['market_id'] = record.market_id
        if hasattr(record, 'user_address'):
            log_data['user_address'] = record.user_address
        if hasattr(record, 'log_index'):
            log_data['log_index'] = record.log_index
        if hasattr(record, 'error'):
            log_data['error'] = record.error
        if hasattr(record, 'duplicate'):
            log_data['duplicate'] = record.duplicate
        if hasattr(record, 'processing_time_ms'):
            log_data['processing_time_ms'] = record.processing_time_ms
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def setup_onchain_logging(log_dir: Optional[str] = None) -> Dict[str, logging.Logger]:
    """
    Setup structured JSON loggers for on-chain events
    
    Args:
        log_dir: Directory for log files (default: predicthub_backend/logs/)
    
    Returns:
        Dictionary of logger instances:
        - 'events': For processed events
        - 'errors': For errors and failures
        - 'duplicates': For duplicate suppression
    """
    if log_dir is None:
        # Get BASE_DIR from Django settings or use default
        try:
            from django.conf import settings
            base_dir = getattr(settings, 'BASE_DIR', None)
            if base_dir:
                log_dir = os.path.join(base_dir, 'logs')
            else:
                log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        except:
            log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    
    # Create log directory if it doesn't exist
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    loggers = {}
    
    # Events logger (onchain_events.jsonl)
    events_logger = logging.getLogger('indexer.events')
    events_logger.setLevel(logging.INFO)
    events_handler = logging.FileHandler(
        os.path.join(log_dir, 'onchain_events.jsonl'),
        mode='a'
    )
    events_handler.setFormatter(JSONFormatter())
    events_logger.addHandler(events_handler)
    events_logger.propagate = False
    loggers['events'] = events_logger
    
    # Errors logger (onchain_errors.jsonl)
    errors_logger = logging.getLogger('indexer.errors')
    errors_logger.setLevel(logging.ERROR)
    errors_handler = logging.FileHandler(
        os.path.join(log_dir, 'onchain_errors.jsonl'),
        mode='a'
    )
    errors_handler.setFormatter(JSONFormatter())
    errors_logger.addHandler(errors_handler)
    errors_logger.propagate = False
    loggers['errors'] = errors_logger
    
    # Duplicates logger (onchain_duplicates.jsonl)
    duplicates_logger = logging.getLogger('indexer.duplicates')
    duplicates_logger.setLevel(logging.DEBUG)
    duplicates_handler = logging.FileHandler(
        os.path.join(log_dir, 'onchain_duplicates.jsonl'),
        mode='a'
    )
    duplicates_handler.setFormatter(JSONFormatter())
    duplicates_logger.addHandler(duplicates_handler)
    duplicates_logger.propagate = False
    loggers['duplicates'] = duplicates_logger
    
    return loggers


def get_onchain_loggers() -> Dict[str, logging.Logger]:
    """Get or create on-chain event loggers"""
    try:
        events_logger = logging.getLogger('indexer.events')
        errors_logger = logging.getLogger('indexer.errors')
        duplicates_logger = logging.getLogger('indexer.duplicates')
        
        # Check if handlers are already set up
        if events_logger.handlers and errors_logger.handlers:
            return {
                'events': events_logger,
                'errors': errors_logger,
                'duplicates': duplicates_logger,
            }
    except:
        pass
    
    # Setup if not already done
    return setup_onchain_logging()

