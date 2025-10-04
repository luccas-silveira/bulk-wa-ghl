"""
GHL Messages API Endpoints
Handles sending WhatsApp messages through GoHighLevel
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, validator
import re

from src.database import get_db
from src.services.ghl_conversations_service import GHLConversationsService, RateLimitExceeded
from src.models.ghl_location import GHLLocation
from src.models.message import Message
from src.models.campaign import Campaign

router = APIRouter(prefix="/ghl/messages", tags=["GHL Messages"])


class SendMessageRequest(BaseModel):
    """Request model for sending a message"""
    ghl_location_id: str = Field(..., description="GHL location identifier")
    contact_phone: str = Field(..., description="Recipient phone number in E.164 format")
    message_text: str = Field(..., min_length=1, description="Message text content")
    media_url: str | None = Field(None, description="Optional media URL")
    campaign_id: int | None = Field(None, description="Optional campaign ID to associate message")

    @validator('contact_phone')
    def validate_phone_format(cls, v):
        """Validate phone number is in E.164 format"""
        # E.164 format: +[country code][number]
        pattern = r'^\+[1-9]\d{1,14}$'
        if not re.match(pattern, v):
            raise ValueError('Phone number must be in E.164 format (e.g., +5511999999999)')
        return v


@router.post("/send", status_code=status.HTTP_201_CREATED)
async def send_message(
    request: SendMessageRequest,
    db: Session = Depends(get_db)
):
    """
    Send a WhatsApp message through GHL

    Request Body:
    - ghl_location_id: GHL location to send from
    - contact_phone: Recipient phone (E.164 format)
    - message_text: Message content
    - media_url: Optional media attachment
    - campaign_id: Optional campaign association

    Returns:
        Message details with GHL message ID

    Raises:
        404: If location not found
        422: If location validation fails
        429: If rate limit exceeded
        400: If sending fails
    """
    # Validate location exists
    location = db.query(GHLLocation).filter(
        GHLLocation.ghl_location_id == request.ghl_location_id
    ).first()

    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location {request.ghl_location_id} not found"
        )

    # Validate location is active
    if not location.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Location {request.ghl_location_id} is not active"
        )

    # Validate location has WhatsApp
    if not location.has_whatsapp:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Location {request.ghl_location_id} does not have WhatsApp enabled"
        )

    # Validate campaign if provided
    campaign = None
    if request.campaign_id:
        campaign = db.query(Campaign).filter(Campaign.id == request.campaign_id).first()
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign {request.campaign_id} not found"
            )

    # Send message through GHL
    conversations_service = GHLConversationsService(db)

    try:
        result = await conversations_service.send_message(
            location_id=request.ghl_location_id,
            contact_phone=request.contact_phone,
            message_text=request.message_text,
            media_url=request.media_url
        )

        # Create message record in database
        message = Message(
            campaign_id=request.campaign_id,
            recipient_phone=request.contact_phone,
            content=request.message_text,
            status="sent",
            ghl_conversation_id=result.get("conversationId"),
            ghl_message_id=result.get("messageId"),
            ghl_status="sent"
        )

        db.add(message)
        db.commit()
        db.refresh(message)

        return {
            "message_id": message.id,
            "ghl_message_id": result.get("messageId"),
            "conversation_id": result.get("conversationId"),
            "contact_id": result.get("contactId"),
            "status": "sent",
            "sent_at": result.get("sentAt"),
            "recipient_phone": request.contact_phone,
            "message_text": request.message_text
        }

    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )


@router.get("/{message_id}")
async def get_message(
    message_id: int,
    db: Session = Depends(get_db)
):
    """
    Get message details by ID

    Path Parameters:
    - message_id: Database message ID

    Returns:
        Message object

    Raises:
        404: If message not found
    """
    message = db.query(Message).filter(Message.id == message_id).first()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message {message_id} not found"
        )

    return message.to_dict()
