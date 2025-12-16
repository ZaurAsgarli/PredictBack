import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_api.core.settings')
django.setup()

from backend_api.api.markets.polymarket_service import PolymarketService

def debug_sync():
    print("--- Starting Service Debug ---")
    service = PolymarketService()
    
    print("Calling fetch_trending_events(limit=5)...")
    try:
        events = service.fetch_trending_events(limit=5)
        print(f"Events returned: {len(events)}")
        
        if not events:
            print("Response was empty.")
        else:
            for i, e in enumerate(events):
                print(f"Event {i}: {e.get('title')}")
                
        print("\nCalling sync_markets()...")
        count = service.sync_markets()
        print(f"Synced Markets Count: {count}")
        
    except Exception as e:
        print(f"Service Call Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_sync()
