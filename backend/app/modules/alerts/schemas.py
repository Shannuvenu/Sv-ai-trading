from pydantic import BaseModel, field_validator
from datetime import datetime
from decimal import Decimal


class AlertCreate(BaseModel):
    symbol: str
    alert_type: str
    threshold_value: Decimal | None = None


class AlertResponse(BaseModel):
    id: int
    symbol: str
    alert_type: str
    threshold_value: Decimal | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationResponse(BaseModel):
    id: int
    message: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
