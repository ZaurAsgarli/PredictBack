from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
import hmac
import hashlib
import json
from django.conf import settings
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt

from markets.models import Market
from .models import OnchainTransaction, OnchainEventLog


INDEXER_WEBHOOK_SECRET = getattr(settings, "INDEXER_WEBHOOK_SECRET", "supersecret")


class OnchainWebhookView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        # 1) Validate secret header
        secret = request.headers.get("X-Indexer-Secret") or request.META.get(
            "HTTP_X_INDEXER_SECRET"
        )
        if secret != INDEXER_WEBHOOK_SECRET:
            return Response(
                {"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN
            )

        try:
            payload = request.data if isinstance(request.data, dict) else json.loads(
                request.body or "{}"
            )
        except json.JSONDecodeError:
            return Response(
                {"detail": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST
            )

        event_name = payload.get("event_name")
        tx_hash = payload.get("tx_hash")
        log_index = payload.get("log_index")
        block_number = payload.get("block_number")
        market_id = payload.get("market_id")
        user_address = payload.get("user_address") or ""
        event_payload = payload.get("payload") or {}

        if event_name is None or tx_hash is None or log_index is None:
            return Response(
                {"detail": "event_name, tx_hash and log_index are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            log_index = int(log_index)
        except (TypeError, ValueError):
            return Response(
                {"detail": "log_index must be an integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if block_number is not None:
            try:
                block_number = int(block_number)
            except (TypeError, ValueError):
                block_number = None

        with transaction.atomic():
            # 3) Get or create OnchainTransaction
            tx, created_tx = OnchainTransaction.objects.get_or_create(
                tx_hash=tx_hash,
                defaults={
                    "network": "sepolia",
                    "block_number": block_number,
                },
            )

            if not created_tx and block_number is not None:
                tx.block_number = block_number
                tx.save(update_fields=["block_number", "updated_at"])

            # 4) Create or get OnchainEventLog using (tx_hash, log_index)
            event, created_event = OnchainEventLog.objects.get_or_create(
                tx_hash=tx_hash,
                log_index=log_index,
                defaults={
                    "onchain_tx": tx,
                    "event_name": event_name,
                    "user_address": user_address,
                    "payload_json": event_payload,
                },
            )

            duplicate = not created_event
            if duplicate:
                event.duplicate = True

            event.onchain_tx = tx
            event.event_name = event_name
            event.user_address = user_address
            event.payload_json = event_payload

            # 6) Optional market
            if market_id is not None:
                try:
                    market = Market.objects.get(pk=market_id)
                    event.market = market
                except Market.DoesNotExist:
                    pass

            event.save()

        return Response(
            {"status": "ok", "duplicate": duplicate},
            status=status.HTTP_201_CREATED,
        )


@csrf_exempt
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def webhook_handler(request):
    """
    Webhook endpoint for future on-chain indexer
    This will receive events from blockchain indexers
    """
    # Verify webhook signature if configured
    webhook_secret = getattr(settings, 'WEBHOOK_SECRET', None)
    if webhook_secret:
        signature = request.headers.get('X-Webhook-Signature', '')
        payload = request.body
        expected_signature = hmac.new(
            webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return Response(
                {'error': 'Invalid signature'},
                status=status.HTTP_401_UNAUTHORIZED
            )
    
    # Process webhook payload
    try:
        data = json.loads(request.body)
        event_type = data.get('type')
        
        # Placeholder for future implementation
        # This would handle:
        # - AMM pricing updates
        # - Oracle callbacks
        # - Market resolution events
        # - Liquidity pool changes
        
        return Response({
            'status': 'received',
            'event_type': event_type
        })
    except json.JSONDecodeError:
        return Response(
            {'error': 'Invalid JSON'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def rpc_endpoint(request):
    """
    RPC endpoint for future AMM feeds
    """
    # Placeholder for RPC implementation
    return Response({
        'status': 'RPC endpoint ready',
        'version': '1.0'
    })
