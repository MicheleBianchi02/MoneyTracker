from datetime import date

from pydantic import BaseModel


class TransactionIn(BaseModel):
    primary: str
    secondary: str | None
    tr_type: str
    tr_date: date
    name: str
    value: float
    currency: str
    description: str


class TransactionOut(BaseModel):
    id: int
    id_user: int
    primary: str
    secondary: str | None
    tr_type: str
    tr_date: date
    name: str
    value: float
    currency: str
    description: str
