import requests
import random
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from backend_api.api.markets.models import Market, MarketCategory

class PolymarketService:
    BASE_URL = "https://gamma-api.polymarket.com/events"

    def fetch_trending_events(self, limit=20):
        """
        Fetch trending events from Polymarket Gamma API.
        """
        params = {
            "limit": limit
        }
        try:
            response = requests.get(self.BASE_URL, params=params)
            if response.status_code != 200:
                print(f"Polymarket API Error: {response.status_code} - {response.text}")
                return []
            return response.json()
        except Exception as e:
            print(f"Error fetching Polymarket data: {e}")
            return []

    def sync_markets(self):
        """
        Fetch and sync markets to the local database.
        """
        events = self.fetch_trending_events(limit=20)
        
        # Ensure 'Trending' category exists
        category, _ = MarketCategory.objects.get_or_create(
            name="Trending",
            defaults={"slug": "trending", "description": "Top trending markets from Polymarket"}
        )

        synced_count = 0
        for event in events:
            try:
                # Map fields
                title = event.get('title')
                description = event.get('description', '')
                # Polymarket endpoint structure varies; sometimes 'endDate' is in top level or 'markets' list
                # We'll try to find the first market in the event to get the deadline
                markets_list = event.get('markets', [])
                if not markets_list:
                    continue
                
                # Use the first market's end date
                end_date_str = markets_list[0].get('endDate')
                if not end_date_str:
                    # Default to 30 days from now if missing
                    ends_at = timezone.now() + timedelta(days=30)
                else:
                    # Parse ISO format (e.g. 2024-11-05T00:00:00Z)
                    try:
                        ends_at = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                    except ValueError:
                        ends_at = timezone.now() + timedelta(days=30)

                # Create or Update Market
                # We use title as a rough unique key for this demo script 
                # (In prod, store external ID)
                market, created = Market.objects.update_or_create(
                    title=title,
                    defaults={
                        "description": description or title,
                        "category": category,
                        "ends_at": ends_at,
                        "status": "active",
                        # Simulate liquidity based on Polymarket volume (randomized scaling)
                        "liquidity_pool": float(event.get('volume', 0)) / 1000.0, 
                        "onchain_market_id": int(event.get('id', 0)) if str(event.get('id', 0)).isdigit() else None
                    }
                )
                synced_count += 1
            except Exception as e:
                print(f"Failed to sync event {event.get('title')}: {e}")
        
        return synced_count
