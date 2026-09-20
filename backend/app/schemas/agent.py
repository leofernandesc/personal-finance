from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.schemas.common import APIModel, validate_money


class AgentDatedRequest(APIModel):
    transaction_date: date | None = None
    relative_date: Literal["today", "yesterday", "tomorrow"] | None = None

    @model_validator(mode="after")
    def one_date_source(self):
        if self.transaction_date is not None and self.relative_date is not None:
            raise ValueError("Informe uma data absoluta ou relativa, não ambas")
        return self


class AgentTransactionRequest(AgentDatedRequest):
    type: Literal["income", "expense"]
    amount: Decimal = Field(gt=Decimal("0.00"), max_digits=14, decimal_places=2)
    description: str = Field(default="", max_length=255)
    account_name: str | None = Field(default=None, max_length=80)
    category_name: str | None = Field(default=None, max_length=80)

    @field_validator("account_name", "category_name")
    @classmethod
    def clean_optional_name(cls, value: str | None) -> str | None:
        cleaned = value.strip() if value else None
        return cleaned or None

    @field_validator("amount")
    @classmethod
    def valid_amount(cls, value: Decimal) -> Decimal:
        return validate_money(value)


class AgentTransferRequest(AgentDatedRequest):
    amount: Decimal = Field(gt=Decimal("0.00"), max_digits=14, decimal_places=2)
    source_account_name: str = Field(min_length=1, max_length=80)
    destination_account_name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="Transferência", max_length=255)

    @field_validator("amount")
    @classmethod
    def valid_amount(cls, value: Decimal) -> Decimal:
        return validate_money(value)

    @field_validator("source_account_name", "destination_account_name")
    @classmethod
    def clean_account_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Informe a conta")
        return cleaned


class AgentTransactionUpdateRequest(AgentDatedRequest):
    transaction_id: UUID
    amount: Decimal | None = Field(
        default=None, gt=Decimal("0.00"), max_digits=14, decimal_places=2
    )
    description: str | None = Field(default=None, max_length=255)
    category_name: str | None = Field(default=None, max_length=80)

    @field_validator("amount")
    @classmethod
    def valid_amount(cls, value: Decimal | None) -> Decimal | None:
        return validate_money(value) if value is not None else None


class AgentBudgetRequest(APIModel):
    category_name: str = Field(min_length=1, max_length=80)
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

    @field_validator("name")
    @classmethod
    def clean_goal_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Informe o nome da meta")
        return cleaned

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
