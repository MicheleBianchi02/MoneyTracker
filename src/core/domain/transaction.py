from dataclasses import dataclass
from datetime import date
from typing import Literal

from pydantic import BaseModel

# from src.core.exceptions import InvalidCurrencyException
# from src.core.services.exc_rate_service import exc_rate_service


@dataclass
class TransactionRepoIn:
    id_user: int
    id_cat: int
    tr_date: date
    name: str
    value: float
    currency: str
    description: str


class TransactionIn(BaseModel):
    primary: str
    secondary: str | None
    tr_type: Literal["income", "expense"]
    tr_date: date
    name: str
    value: float
    currency: str
    description: str

    # this check is already performed in the service layer
    # @validator("currency")
    # def validate_currency(cls, v):
    #     """Check that the currency is one of the available currencies."""
    #     v_upper = v.upper()
    #     if not exc_rate_service.validate_currency(v_upper):
    #         raise InvalidCurrencyException(v_upper)
    #     return v_upper


class TransactionOut(BaseModel):
    id: int
    id_user: int
    primary: str
    secondary: str | None
    tr_type: Literal["income", "expense"]
    tr_date: date
    name: str
    value: float
    currency: str
    description: str
