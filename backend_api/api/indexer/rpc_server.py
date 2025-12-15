"""
JSON-RPC server stub for admin integration.

This provides a JSON-RPC 2.0 compatible interface for administrative operations.
Can be extended to support gRPC if needed.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View

from django.db import models
from backend_api.api.indexer.models import OnchainTransaction, OnchainEventLog
from backend_api.api.markets.models import Market
from backend_api.api.trades.models import Trade
from backend_api.api.liquidity.models import LiquidityEvent
from backend_api.api.users.models import User

logger = logging.getLogger(__name__)


class JSONRPCHandler:
    """Handles JSON-RPC 2.0 requests"""
    
    def __init__(self):
        self.methods = {
            'get_indexer_status': self.get_indexer_status,
            'get_latest_block': self.get_latest_block,
            'get_event_count': self.get_event_count,
            'get_user_by_address': self.get_user_by_address,
            'get_market_by_onchain_id': self.get_market_by_onchain_id,
            'get_transaction_by_hash': self.get_transaction_by_hash,
            'list_recent_events': self.list_recent_events,
            'get_system_health': self.get_system_health,
        }
    
    def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a JSON-RPC request"""
        method = request_data.get('method')
        params = request_data.get('params', {})
        request_id = request_data.get('id')
        
        if not method:
            return {
                'jsonrpc': '2.0',
                'error': {
                    'code': -32600,
                    'message': 'Invalid Request',
                },
                'id': request_id,
            }
        
        if method not in self.methods:
            return {
                'jsonrpc': '2.0',
                'error': {
                    'code': -32601,
                    'message': 'Method not found',
                },
                'id': request_id,
            }
        
        try:
            result = self.methods[method](params)
            return {
                'jsonrpc': '2.0',
                'result': result,
                'id': request_id,
            }
        except Exception as e:
            logger.error(f"Error executing {method}: {e}", exc_info=True)
            return {
                'jsonrpc': '2.0',
                'error': {
                    'code': -32603,
                    'message': 'Internal error',
                    'data': str(e),
                },
                'id': request_id,
            }
    
    def get_indexer_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get indexer status"""
        latest_tx = OnchainTransaction.objects.order_by('-block_number').first()
        event_count = OnchainEventLog.objects.count()
        processed_count = OnchainEventLog.objects.filter(processed_at__isnull=False).count()
        
        return {
            'status': 'running',
            'latest_block': latest_tx.block_number if latest_tx else None,
            'total_events': event_count,
            'processed_events': processed_count,
            'pending_events': event_count - processed_count,
        }
    
    def get_latest_block(self, params: Dict[str, Any]) -> Optional[int]:
        """Get latest processed block number"""
        latest_tx = OnchainTransaction.objects.order_by('-block_number').first()
        return latest_tx.block_number if latest_tx else None
    
    def get_event_count(self, params: Dict[str, Any]) -> Dict[str, int]:
        """Get event counts by type"""
        event_types = OnchainEventLog.objects.values('event_name').annotate(
            count=models.Count('id')
        )
        return {item['event_name']: item['count'] for item in event_types}
    
    def get_user_by_address(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get user by wallet address"""
        address = params.get('address')
        if not address:
            raise ValueError("address parameter required")
        
        # This assumes you have a wallet_address field on User
        # If not, you'd need to add it or use a different lookup
        try:
            user = User.objects.get(username=address)  # Simplified - adjust based on your schema
            return {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'created_at': user.created_at.isoformat(),
            }
        except User.DoesNotExist:
            return None
    
    def get_market_by_onchain_id(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get market by onchain market ID"""
        market_id = params.get('market_id')
        if not market_id:
            raise ValueError("market_id parameter required")
        
        try:
            market = Market.objects.get(onchain_market_id=market_id)
            return {
                'id': market.id,
                'onchain_market_id': market.onchain_market_id,
                'title': market.title,
                'status': market.status,
                'liquidity_pool': str(market.liquidity_pool),
            }
        except Market.DoesNotExist:
            return None
    
    def get_transaction_by_hash(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get transaction by hash"""
        tx_hash = params.get('tx_hash')
        if not tx_hash:
            raise ValueError("tx_hash parameter required")
        
        try:
            tx = OnchainTransaction.objects.get(tx_hash=tx_hash)
            events = OnchainEventLog.objects.filter(onchain_tx=tx).values(
                'event_name', 'log_index', 'payload_json'
            )
            return {
                'tx_hash': tx.tx_hash,
                'block_number': tx.block_number,
                'status': tx.status,
                'network': tx.network,
                'events': list(events),
            }
        except OnchainTransaction.DoesNotExist:
            return None
    
    def list_recent_events(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List recent events"""
        limit = params.get('limit', 10)
        event_name = params.get('event_name')
        
        queryset = OnchainEventLog.objects.order_by('-created_at')
        if event_name:
            queryset = queryset.filter(event_name=event_name)
        
        events = queryset[:limit]
        return [
            {
                'event_name': e.event_name,
                'tx_hash': e.tx_hash,
                'log_index': e.log_index,
                'user_address': e.user_address,
                'created_at': e.created_at.isoformat(),
                'processed_at': e.processed_at.isoformat() if e.processed_at else None,
            }
            for e in events
        ]
    
    def get_system_health(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get system health metrics"""
        from django.db import models
        
        return {
            'database': {
                'markets': Market.objects.count(),
                'trades': Trade.objects.count(),
                'liquidity_events': LiquidityEvent.objects.count(),
                'users': User.objects.count(),
            },
            'indexer': {
                'total_transactions': OnchainTransaction.objects.count(),
                'total_events': OnchainEventLog.objects.count(),
                'failed_transactions': OnchainTransaction.objects.filter(status='FAILED').count(),
            },
        }


@csrf_exempt
@require_http_methods(["POST"])
def jsonrpc_endpoint(request):
    """JSON-RPC 2.0 endpoint"""
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            return JsonResponse({
                'jsonrpc': '2.0',
                'error': {
                    'code': -32600,
                    'message': 'Invalid Request - Content-Type must be application/json',
                },
                'id': None,
            }, status=400)
        
        # Handle batch requests
        if isinstance(data, list):
            handler = JSONRPCHandler()
            results = [handler.handle_request(item) for item in data]
            return JsonResponse(results, safe=False)
        else:
            handler = JSONRPCHandler()
            result = handler.handle_request(data)
            return JsonResponse(result)
    
    except json.JSONDecodeError:
        return JsonResponse({
            'jsonrpc': '2.0',
            'error': {
                'code': -32700,
                'message': 'Parse error',
            },
            'id': None,
        }, status=400)
    except Exception as e:
        logger.error(f"Error in JSON-RPC endpoint: {e}", exc_info=True)
        return JsonResponse({
            'jsonrpc': '2.0',
            'error': {
                'code': -32603,
                'message': 'Internal error',
                'data': str(e),
            },
            'id': None,
        }, status=500)

