"""
GHL Webhooks API Endpoints
Handles incoming webhooks from GoHighLevel
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Optional

from src.database import get_db
from src.services.ghl_webhook_handler import GHLWebhookHandler

logger = logging.getLogger(__name__)


class WebhookPayload(BaseModel):
    """Schema Pydantic para validação de webhooks GHL (GHL-13)."""
    type: str = Field(..., description="Webhook event type")
    locationId: str = Field(..., description="GHL location ID")
    messageId: Optional[str] = None
    conversationId: Optional[str] = None
    contactId: Optional[str] = None
    contactPhone: Optional[str] = None
    messageText: Optional[str] = None
    timestamp: Optional[str] = None
    errorCode: Optional[str] = None
    errorMessage: Optional[str] = None

router = APIRouter(prefix="/webhooks/ghl", tags=["GHL Webhooks"])
logger = logging.getLogger(__name__)


@router.post("/messages", status_code=status.HTTP_200_OK)
async def process_webhook(
    request: Request,
    x_ghl_signature: str = Header(None, alias="X-GHL-Signature"),
    db: AsyncSession = Depends(get_db)
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
    client_ip = request.client.host if request.client else "unknown"

    # Get raw payload for signature validation
    raw_payload = await request.body()

    # GHL-21: reject oversized payloads before any processing
    if len(raw_payload) > 1_000_000:
        raise HTTPException(
            status_code=413,
            detail="Webhook payload exceeds 1MB limit"
        )

    # Extract webhook_id from payload if possible (for logging before full parse)
    webhook_id_for_log = None
    try:
        partial = json.loads(raw_payload)
        webhook_id_for_log = partial.get("messageId") or partial.get("id")
    except Exception:
        pass

    # Validate signature presence
    if not x_ghl_signature:
        logger.warning(
            "Webhook signature missing",
            extra={"client_ip": client_ip, "webhook_id": webhook_id_for_log}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-GHL-Signature header"
        )

    webhook_handler = GHLWebhookHandler(db)

    if not webhook_handler.validate_signature(raw_payload, x_ghl_signature):
        # GHL-26: log warning with client IP for audit
        logger.warning(
            f"Webhook signature validation failed for webhook_id={webhook_id_for_log} from {client_ip} — possible replay/spoofing attempt",
            extra={"client_ip": client_ip, "webhook_id": webhook_id_for_log}
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

    # GHL-13: validate payload structure
    try:
        WebhookPayload.model_validate(payload)
    except ValidationError:
        raise HTTPException(
            status_code=422,
            detail="Invalid webhook payload: missing required fields"
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
