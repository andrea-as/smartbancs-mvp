from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, Field, field_validator


class BancsLegacyEvent(BaseModel):
    legacy_id: str = Field(min_length=1, max_length=80)
    source_account: str = Field(min_length=3, max_length=40)
    destination_account: str = Field(min_length=3, max_length=40)
    amount: str
    currency: str = Field(min_length=3, max_length=3)
    event_time: str

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    def to_canonical(self) -> dict:
        try:
            amount = Decimal(self.amount.strip()).quantize(Decimal("0.01"))
        except (InvalidOperation, AttributeError) as exc:
            raise ValueError("Monto Bancs inválido") from exc
        if amount <= 0:
            raise ValueError("Monto Bancs debe ser positivo")
        event_time = datetime.fromisoformat(self.event_time.replace("Z", "+00:00"))
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)
        return {
            "legacy_id": self.legacy_id.strip(),
            "source_account": self.source_account.strip().upper(),
            "destination_account": self.destination_account.strip().upper(),
            "amount": str(amount),
            "currency": self.currency,
            "event_time": event_time.isoformat(),
        }
