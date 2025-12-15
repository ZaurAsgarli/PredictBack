"""
Django management command to run the indexer (WebSocket + HTTP polling)
"""
import asyncio
import time
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from backend_api.core.utils.contracts import get_contract_service
from backend_api.api.indexer.services import EventProcessor
from backend_api.api.indexer.services.listener import EventListener
from backend_api.api.indexer.services.event_decoder import EventDecoder

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run the blockchain indexer (WebSocket + HTTP polling)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--poll-interval',
            type=int,
            default=12,
            help='HTTP polling interval in seconds (default: 12)',
        )
        parser.add_argument(
            '--from-block',
            type=int,
            default=None,
            help='Start from block number (default: latest - 100)',
        )
        parser.add_argument(
            '--use-websocket',
            action='store_true',
            help='Use WebSocket for real-time events (requires WEB3_PROVIDER_WS)',
        )

    def handle(self, *args, **options):
        poll_interval = options['poll_interval']
        from_block = options['from_block']
        use_websocket = options['use_websocket']
        
        contract_service = get_contract_service()
        if not contract_service.is_connected():
            self.stdout.write(
                self.style.ERROR('Web3 not connected. Check WEB3_PROVIDER_HTTP setting.')
            )
            return
        
        processor = EventProcessor()
        decoder = EventDecoder()
        
        # Get starting block
        if from_block is None:
            latest = contract_service.get_latest_block()
            if latest:
                from_block = max(1, latest - 100)  # Start from 100 blocks ago
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting indexer from block {from_block}')
        )
        
        try:
            if use_websocket and contract_service.w3_async:
                # Use WebSocket for real-time events
                self.stdout.write(self.style.SUCCESS('Using WebSocket for real-time events'))
                listener = EventListener()
                asyncio.run(listener.start(from_block))
            else:
                # Use HTTP polling
                self.stdout.write(self.style.SUCCESS('Using HTTP polling'))
                self._run_polling_indexer(contract_service, processor, decoder, poll_interval, from_block)
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nStopping indexer...'))
        except Exception as e:
            logger.error(f"Error in indexer: {e}", exc_info=True)
            self.stdout.write(
                self.style.ERROR(f'Error: {e}')
            )
    
    def _run_polling_indexer(self, contract_service, processor, decoder, poll_interval, from_block):
        """Run indexer with HTTP polling"""
        last_processed_block = from_block
        
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
                duplicate_count = 0
                error_count = 0
                
                for event in events:
                    decoded = decoder.decode(event)
                    if decoded:
                        result = processor.process_event(decoded)
                        if result['success']:
                            processed_count += 1
                        elif result.get('duplicate'):
                            duplicate_count += 1
                        else:
                            error_count += 1
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Processed {processed_count} events, {duplicate_count} duplicates, {error_count} errors'
                    )
                )
                
                last_processed_block = current_block
            else:
                self.stdout.write('No new blocks, waiting...')
            
            time.sleep(poll_interval)
