"""
GHL Webhooks API Endpoints
Handles incoming webhooks from GoHighLevel
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy.orm import Session
from typing import Dict

from src.database import get_db
from src.services.ghl_webhook_handler import GHLWebhookHandler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/ghl", tags=["GHL Webhooks"])


@router.post("/messages", status_code=status.HTTP_200_OK)
async def process_webhook(
    request: Request,
    x_ghl_signature: str = Header(None, alias="X-GHL-Signature"),
    db: Session = Depends(get_db)
):
    """
    Process incoming webhook from GoHighLevel

    Headers:
    - X-GHL-Signature: HMAC-SHA256 signature for validation

    Request Body:
        Webhook payload with event data

    Returns:
        Processing result

    Raises:
        413: If payload exceeds 1MB limit
        401: If signature validation fails
        400: If webhook processing fails
    """
    # Get raw payload for signature validation
    raw_payload = await request.body()

    # GHL-21: reject oversized payloads before any processing
    if len(raw_payload) > 1_000_000:
        raise HTTPException(
            status_code=413,
            detail="Webhook payload exceeds 1MB limit"
        )

    # Validate signature
    if not x_ghl_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-GHL-Signature header"
        )

    webhook_handler = GHLWebhookHandler(db)

    if not webhook_handler.validate_signature(raw_payload, x_ghl_signature):
        # GHL-26: log warning with client IP for audit
        client_ip = request.client.host if request.client else "unknown"
        logger.warning(
            "Webhook signature validation failed — possible replay/spoofing attempt",
            extra={"client_ip": client_ip}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )

    # Parse payload
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON payload: {str(e)}"
        )

    # Extract event type
    event_type = payload.get("type")
    if not event_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'type' field in webhook payload"
        )

    # Process webhook
    try:
        result = await webhook_handler.process_webhook(event_type, payload)

        return {
            "success": True,
            "webhook_id": result.get("webhook_id"),
            "status": result.get("status"),
            "already_processed": result.get("already_processed", False),
            "event_type": event_type
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )
