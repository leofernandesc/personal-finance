from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, extra="forbid")


class MessageResponse(APIModel):
    message: str


class UUIDResponse(APIModel):
    id: UUID


def validate_money(value: Decimal) -> Decimal:
    if value.as_tuple().exponent < -2:
        raise ValueError("Use no máximo duas casas decimais")
    return value.quantize(Decimal("0.01"))


class MoneyField(APIModel):
    amount: Decimal = Field(gt=Decimal("0.00"), max_digits=14, decimal_places=2)

    @field_validator("amount")
    @classmethod
    def amount_has_two_places(cls, value: Decimal) -> Decimal:
        return validate_money(value)


def dump_decimal(value: Decimal | None) -> str | None:
    return str(value.quantize(Decimal("0.01"))) if value is not None else None
