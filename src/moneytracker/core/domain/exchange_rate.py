from dataclasses import dataclass
from datetime import date

from pydantic import BaseModel


@dataclass
class ExchangeRate:
    from_currency: str  # base currency, eg "EUR". Symbol like "€" are not correct
    to_currency: str
    rate: float
    rate_date: date
    is_updated: bool


class Currency(BaseModel):
    code: str
    symbol: str
    name: str
    is_active: bool
    deprecation_date: date | None
