"""
Django management command to backfill historical blockchain events
"""
import logging
from django.core.management.base import BaseCommand
from indexer.services.backfill import BackfillService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Backfill historical blockchain events'

    def add_arguments(self, parser):
        parser.add_argument(
            '--from',
            type=int,
            dest='from_block',
            default=0,
            help='Start block number (default: 0)',
        )
        parser.add_argument(
            '--to',
            type=str,
            dest='to_block',
            default='latest',
            help='End block number or "latest" (default: latest)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of blocks to process per batch (default: 1000)',
        )

    def handle(self, *args, **options):
        from_block = options['from_block']
        to_block_str = options['to_block']
        batch_size = options['batch_size']
        
        backfill_service = BackfillService()
        
        # Parse to_block
        if to_block_str == 'latest':
            to_block = None
        else:
            try:
                to_block = int(to_block_str)
            except ValueError:
                self.stdout.write(self.style.ERROR(f'Invalid to_block: {to_block_str}'))
                return
        
        try:
            result = backfill_service.backfill(
                from_block=from_block,
                to_block=to_block,
                batch_size=batch_size
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nBackfill complete!\n'
                    f'Duration: {result["duration_seconds"]:.2f} seconds\n'
                    f'Events processed: {result["total_events_processed"]}/{result["total_events_found"]}\n'
                    f'Duplicates: {result["total_duplicates"]}\n'
                    f'Errors: {result["total_errors"]}\n'
                )
            )
            
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nBackfill interrupted'))
        except Exception as e:
            logger.error(f"Error in backfill: {e}", exc_info=True)
            self.stdout.write(
                self.style.ERROR(f'Error: {e}')
            )
