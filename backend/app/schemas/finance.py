from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.schemas.common import APIModel, validate_money

AccountType = Literal["checking", "savings", "cash", "investment", "other"]
CategoryKind = Literal["expense", "income", "both"]
TransactionType = Literal["income", "expense", "transfer"]
SourceType = Literal["web", "whatsapp", "import", "automatic"]
TransactionSort = Literal["date_desc", "date_asc", "amount_desc", "amount_asc"]


def clean_name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Informe um nome")
    return cleaned


class AccountCreate(APIModel):
    name: str = Field(min_length=1, max_length=80)
    account_type: AccountType = "checking"
    opening_balance: Decimal = Field(default=Decimal("0.00"), max_digits=14, decimal_places=2)

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        return clean_name(value)

    @field_validator("opening_balance")
    @classmethod
    def valid_opening_balance(cls, value: Decimal) -> Decimal:
        return validate_money(value)


class AccountUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    account_type: AccountType | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str | None) -> str | None:
        return clean_name(value) if value is not None else None


class AccountResponse(APIModel):
    id: UUID
    name: str
    account_type: AccountType
    opening_balance: Decimal
    is_active: bool
    balance: Decimal = Decimal("0.00")


class CategoryCreate(APIModel):
    name: str = Field(min_length=1, max_length=80)
    kind: CategoryKind = "expense"
    parent_id: UUID | None = None

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        return clean_name(value)


class CategoryUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    kind: CategoryKind | None = None
    parent_id: UUID | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str | None) -> str | None:
        return clean_name(value) if value is not None else None


class CategoryResponse(APIModel):
    id: UUID
    name: str
    kind: CategoryKind
    parent_id: UUID | None
    is_active: bool


class TransactionCreate(APIModel):
    account_id: UUID
    category_id: UUID | None = None
    type: TransactionType
    amount: Decimal = Field(gt=Decimal("0.00"), max_digits=14, decimal_places=2)
    description: str = Field(default="", max_length=255)
    transaction_date: date | None = None
    source: SourceType = "web"
    idempotency_key: str | None = Field(default=None, max_length=255)

    @field_validator("amount")
    @classmethod
    def valid_amount(cls, value: Decimal) -> Decimal:
        return validate_money(value)

    @model_validator(mode="after")
    def no_category_for_transfer(self):
        if self.type == "transfer":
            raise ValueError("Use o endpoint de transferências para transferências")
        return self


class TransactionUpdate(APIModel):
    account_id: UUID | None = None
    category_id: UUID | None = None
    amount: Decimal | None = Field(
        default=None, gt=Decimal("0.00"), max_digits=14, decimal_places=2
    )
    description: str | None = Field(default=None, max_length=255)
    transaction_date: date | None = None

    @field_validator("amount")
    @classmethod
    def valid_amount(cls, value: Decimal | None) -> Decimal | None:
        return validate_money(value) if value is not None else None


class TransactionResponse(APIModel):
    id: UUID
    account_id: UUID
    category_id: UUID | None
    transfer_id: UUID | None
    type: TransactionType
    transfer_leg: str | None
    description: str
    amount: Decimal
    transaction_date: date
    source: SourceType
    created_at: datetime
    account_name: str | None = None
    category_name: str | None = None
    transfer_source_account_name: str | None = None
    transfer_destination_account_name: str | None = None


class TransferCreate(APIModel):
    source_account_id: UUID
    destination_account_id: UUID
    amount: Decimal = Field(gt=Decimal("0.00"), max_digits=14, decimal_places=2)
    description: str = Field(default="Transferência", max_length=255)
    transaction_date: date | None = None
    source: SourceType = "web"
    idempotency_key: str | None = Field(default=None, max_length=255)

    @field_validator("amount")
    @classmethod
    def valid_amount(cls, value: Decimal) -> Decimal:
        return validate_money(value)

    @model_validator(mode="after")
    def accounts_are_different(self):
        if self.source_account_id == self.destination_account_id:
            raise ValueError("As contas da transferência devem ser diferentes")
        return self


class TransferResponse(APIModel):
    id: UUID
    source_account_id: UUID
    destination_account_id: UUID
    amount: Decimal
    description: str
    transaction_date: date
    source: SourceType


class BudgetCreate(APIModel):
    category_id: UUID
    month: date
    limit_amount: Decimal = Field(gt=Decimal("0.00"), max_digits=14, decimal_places=2)

    @field_validator("limit_amount")
    @classmethod
    def valid_limit(cls, value: Decimal) -> Decimal:
        return validate_money(value)

    @field_validator("month")
    @classmethod
    def first_day_of_month(cls, value: date) -> date:
        return value.replace(day=1)


class BudgetUpdate(APIModel):
    limit_amount: Decimal = Field(gt=Decimal("0.00"), max_digits=14, decimal_places=2)

    @field_validator("limit_amount")
    @classmethod
    def valid_limit(cls, value: Decimal) -> Decimal:
        return validate_money(value)


class BudgetResponse(APIModel):
    id: UUID
    category_id: UUID
    category_name: str
    month: date
    limit_amount: Decimal
    spent_amount: Decimal
    remaining_amount: Decimal
    utilization_percent: Decimal
    exceeded_amount: Decimal


class GoalCreate(APIModel):
    name: str = Field(min_length=1, max_length=120)
    target_amount: Decimal = Field(gt=Decimal("0.00"), max_digits=14, decimal_places=2)
    current_amount: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00"), max_digits=14, decimal_places=2
    )
    deadline: date | None = None
    status: Literal["active", "completed", "archived"] = "active"

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        return clean_name(value)

    @field_validator("target_amount", "current_amount")
    @classmethod
    def valid_goal_money(cls, value: Decimal) -> Decimal:
        return validate_money(value)


class GoalUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    target_amount: Decimal | None = Field(
        default=None, gt=Decimal("0.00"), max_digits=14, decimal_places=2
    )
    current_amount: Decimal | None = Field(
        default=None, ge=Decimal("0.00"), max_digits=14, decimal_places=2
    )
    deadline: date | None = None
    status: Literal["active", "completed", "archived"] | None = None

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str | None) -> str | None:
        return clean_name(value) if value is not None else None

    @field_validator("target_amount", "current_amount")
    @classmethod
    def valid_goal_update_money(cls, value: Decimal | None) -> Decimal | None:
        return validate_money(value) if value is not None else None


class GoalResponse(APIModel):
    id: UUID
    name: str
    target_amount: Decimal
    current_amount: Decimal
    deadline: date | None
    status: str
