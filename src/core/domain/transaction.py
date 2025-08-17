from datetime import date

from pydantic import BaseModel


class TransactionIn(BaseModel):
    id_user: int
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


class Transaction(BaseModel):
    id_user: int
    id_category: int
    date: date
    name: str
    value: float
    currency: str
    description: str
    id: int = 1  # This value is defined by the database.

    # def __eq__(self, other):
    #     """Ignore the .id parameter when equating two Transaction
    #
    #     Need this because the .id parameter is noramlly set automatically by the
    #     database, meaning that is a priori unknown.
    #     This is needed, for istance during testing.
    #     """
    #
    #     if not isinstance(other, Transaction):
    #         raise NotImplementedError(
    #             f"Equivalence between Transaction and {type(other)} is not supported",
    #         )
    #
    #     return (
    #         self.id_user,
    #         self.id_category,
    #         self.date,
    #         self.name,
    #         self.value,
    #         self.description,
    #         self.currency,
    #     ) == (
    #         other.id_user,
    #         other.id_category,
    #         other.date,
    #         other.name,
    #         other.value,
    #         other.description,
    #         other.currency,
    #     )
