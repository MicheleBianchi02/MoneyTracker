from dataclasses import dataclass
from datetime import date


@dataclass
class ExchangeRate:
    from_currency: str  # base currency, eg "EUR". Symbol like "€" are not correct
    to_currency: str
    rate: float
    rate_date: date
    is_updated: bool
