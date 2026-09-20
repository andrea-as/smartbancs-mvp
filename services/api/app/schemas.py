from decimal import Decimal
from pydantic import BaseModel, Field, field_validator

class TransferRequest(BaseModel):
    source_account: str = Field(min_length=3, max_length=40)
    destination_account: str = Field(min_length=3, max_length=40)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        return value.upper()
