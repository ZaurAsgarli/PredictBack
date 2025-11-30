"""
Django management command to listen for blockchain events
"""
import time
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from utils.contracts import get_contract_service
from indexer.services import EventProcessor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Listen for blockchain events and process them'

    def add_arguments(self, parser):
        parser.add_argument(
            '--poll-interval',
            type=int,
            default=12,
            help='Polling interval in seconds (default: 12)',
        )
        parser.add_argument(
            '--from-block',
            type=int,
            default=None,
            help='Start from block number (default: latest)',
        )

    def handle(self, *args, **options):
        poll_interval = options['poll_interval']
        from_block = options['from_block']
        
        contract_service = get_contract_service()
        if not contract_service.is_connected():
            self.stdout.write(
                self.style.ERROR('Web3 not connected. Check WEB3_PROVIDER_URL setting.')
            )
            return
        
        processor = EventProcessor()
        
        # Get starting block
        if from_block is None:
            from_block = contract_service.get_latest_block()
            if from_block:
                from_block = max(1, from_block - 100)  # Start from 100 blocks ago
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting event listener from block {from_block}')
        )
        
        last_processed_block = from_block
        
        try:
            while True:
                current_block = contract_service.get_latest_block()
                
                if current_block and current_block > last_processed_block:
                    self.stdout.write(
                        f'Processing blocks {last_processed_block + 1} to {current_block}'
                    )
                    
                    events = contract_service.get_events(
                        from_block=last_processed_block + 1,
                        to_block=current_block
                    )
                    
                    processed_count = 0
                    for event in events:
                        decoded = contract_service.decode_event(event)
                        if decoded:
                            if processor.process_event(decoded):
                                processed_count += 1
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Processed {processed_count} events from {len(events)} logs'
                        )
                    )
                    
                    last_processed_block = current_block
                else:
                    self.stdout.write('No new blocks, waiting...')
                
                time.sleep(poll_interval)
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nStopping event listener...'))
        except Exception as e:
            logger.error(f"Error in event listener: {e}", exc_info=True)
            self.stdout.write(
                self.style.ERROR(f'Error: {e}')
            )

