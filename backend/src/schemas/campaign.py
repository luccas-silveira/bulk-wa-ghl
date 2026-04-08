"""
Pydantic schemas for campaign creation and validation
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class MessageTemplate(BaseModel):
    text: str = Field(default="", max_length=4096)
    media_url: Optional[str] = None


class ContactData(BaseModel):
    phone_number: str = Field(..., min_length=1)
    name: Optional[str] = ""
    email: Optional[str] = None


class AudienceCriteria(BaseModel):
    csv_data: List[ContactData] = Field(default_factory=list)


class CampaignCreateRequest(BaseModel):
    ghl_location_id: str = Field(..., min_length=1, description="GHL location identifier")
    name: str = Field(default="Nova Campanha", min_length=1, max_length=255)
    ghl_user_id: Optional[str] = None
    ghl_user_ids: Optional[List[str]] = None
    sending_speed: str = Field(default="medium", pattern="^(slow|medium|fast)$")
    schedule_type: str = Field(default="immediate", pattern="^(immediate|scheduled)$")
    scheduled_time: Optional[str] = None
    messages: List[MessageTemplate] = Field(..., min_length=1)
    audience_criteria: AudienceCriteria = Field(default_factory=AudienceCriteria)
