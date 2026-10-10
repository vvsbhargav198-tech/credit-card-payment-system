import re
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


class PaymentRequest(BaseModel):
    

    model_config = ConfigDict(extra="forbid")

    card_id: int = Field(gt=0, description="Id of a card saved through the Django API.", examples=[1])
    amount: Decimal = Field(
        gt=Decimal("0"), le=Decimal("1000000"), max_digits=12, decimal_places=2, examples=["49.99"]
    )
    currency: Literal["USD", "EUR", "GBP", "INR"] = "USD"
    description: str = Field(default="", max_length=255, examples=["Order #1001"])

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str) -> str:
        return CONTROL_CHARS.sub("", value).strip()


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reference: str
    status: Literal["PENDING", "SUCCESS", "FAILED"]
    amount: Decimal
    currency: str
    description: str
    card_id: Optional[int]
    card_last4: str
    failure_reason: str
    created_at: datetime
    updated_at: datetime
