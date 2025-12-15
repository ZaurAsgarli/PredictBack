"""
Django management command to seed knowledge tags
"""

from django.core.management.base import BaseCommand
from backend_api.api.markets.models import KnowledgeTag


class Command(BaseCommand):
    help = 'Seed knowledge tags for markets'

    def handle(self, *args, **options):
        tags_data = [
            {'name': 'Politics', 'slug': 'politics', 'description': 'Political events and elections'},
            {'name': 'Sports', 'slug': 'sports', 'description': 'Sports events and competitions'},
            {'name': 'Technology', 'slug': 'technology', 'description': 'Tech industry and innovations'},
            {'name': 'Economics', 'slug': 'economics', 'description': 'Economic indicators and markets'},
            {'name': 'Entertainment', 'slug': 'entertainment', 'description': 'Entertainment industry'},
            {'name': 'Science', 'slug': 'science', 'description': 'Scientific discoveries and research'},
            {'name': 'Crypto', 'slug': 'crypto', 'description': 'Cryptocurrency and blockchain'},
            {'name': 'Weather', 'slug': 'weather', 'description': 'Weather and climate events'},
        ]
        
        created_count = 0
        for tag_data in tags_data:
            tag, created = KnowledgeTag.objects.get_or_create(
                slug=tag_data['slug'],
                defaults={
                    'name': tag_data['name'],
                    'description': tag_data['description'],
                }
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created tag: {tag.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Tag already exists: {tag.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nSuccessfully seeded {created_count} knowledge tags')
        )

