from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.common import APIModel, validate_money


class AgentTransactionRequest(APIModel):
    type: Literal["income", "expense"]
    amount: Decimal = Field(gt=Decimal("0.00"), max_digits=14, decimal_places=2)
    description: str = Field(default="", max_length=255)
    account_name: str | None = Field(default=None, max_length=80)
    category_name: str | None = Field(default=None, max_length=80)
    transaction_date: date | None = None

    @field_validator("amount")
    @classmethod
    def valid_amount(cls, value: Decimal) -> Decimal:
        return validate_money(value)


class AgentTransferRequest(APIModel):
    amount: Decimal = Field(gt=Decimal("0.00"), max_digits=14, decimal_places=2)
    source_account_name: str
    destination_account_name: str
    description: str = Field(default="Transferência", max_length=255)
    transaction_date: date | None = None

    @field_validator("amount")
    @classmethod
    def valid_amount(cls, value: Decimal) -> Decimal:
        return validate_money(value)


class AgentBudgetRequest(APIModel):
    category_name: str
    limit_amount: Decimal = Field(gt=Decimal("0.00"), max_digits=14, decimal_places=2)
    month: date | None = None

    @field_validator("limit_amount")
    @classmethod
    def valid_amount(cls, value: Decimal) -> Decimal:
        return validate_money(value)


class AgentGoalRequest(APIModel):
    name: str = Field(min_length=1, max_length=120)
    target_amount: Decimal = Field(gt=Decimal("0.00"), max_digits=14, decimal_places=2)
    current_amount: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00"), max_digits=14, decimal_places=2
    )
    deadline: date | None = None

    @field_validator("target_amount", "current_amount")
    @classmethod
    def valid_amount(cls, value: Decimal) -> Decimal:
        return validate_money(value)


class AgentInboundRequest(APIModel):
    external_message_id: str = Field(min_length=1, max_length=255)
    sender_id: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=10000)


class AgentLinkRequest(APIModel):
    phone_e164: str = Field(min_length=8, max_length=32)
