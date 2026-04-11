"""
Pydantic schemas for campaign creation and validation
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional
from datetime import datetime, timezone

try:
    import phonenumbers
    from phonenumbers import PhoneNumberFormat
    _PHONENUMBERS_AVAILABLE = True
except ImportError:  # pragma: no cover — lib must be installed; guard is for mypy/type-checks only
    _PHONENUMBERS_AVAILABLE = False


def normalize_phone(raw: str) -> str:
    """
    Tenta normalizar `raw` para o formato E.164.

    Estratégia:
    1. Tenta parse sem country hint (requer '+' + código de país).
    2. Se falhar, tenta parse forçando BR como país padrão (para cobrir números
       como "5511999998888" sem o '+').
    3. Se ainda assim falhar ou o resultado não for número válido, devolve `raw`
       intacto — sem lançar exceção.

    Args:
        raw: Número de telefone em qualquer formato.

    Returns:
        Número no formato E.164 (e.g. "+5511999998888") ou o valor original.
    """
    if not _PHONENUMBERS_AVAILABLE or not raw:
        return raw

    for region in (None, "BR"):
        try:
            parsed = phonenumbers.parse(raw, region)
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            continue

    return raw


class MessageTemplate(BaseModel):
    text: str = Field(default="", max_length=4096)
    media_url: Optional[str] = None


class ContactData(BaseModel):
    phone_number: str = Field(..., min_length=1)
    name: Optional[str] = ""
    email: Optional[str] = None

    @field_validator('phone_number', mode='before')
    @classmethod
    def normalize_phone_number(cls, v: str) -> str:
        return normalize_phone(v)


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

    @field_validator('scheduled_time', mode='before')
    @classmethod
    def validate_scheduled_time(cls, v):
        if v is None:
            return v
        try:
            dt = datetime.fromisoformat(str(v).replace('Z', '+00:00'))
        except (ValueError, TypeError):
            raise ValueError('Invalid scheduled_time format. Use ISO 8601.')
        if dt <= datetime.now(timezone.utc):
            raise ValueError('scheduled_time must be in the future.')
        return v

    @model_validator(mode='after')
    def validate_scheduled_requires_time(self):
        if self.schedule_type == 'scheduled' and not self.scheduled_time:
            raise ValueError('scheduled_time is required when schedule_type is scheduled.')
        return self
