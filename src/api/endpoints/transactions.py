from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.dependencies import get_id_user
from core.domain.transaction import TransactionIn, TransactionOut
from core.exceptions import (
    BadRequestException,
    CategoryNotFoundException,
    ForbiddenException,
    InternalServerErrorException,
    InvalidCurrencyException,
    OperationNotPermittedError,
    ServiceCategoryNotFoundError,
    ServiceError,
    ServiceExchangeRateNotFoundError,
    ServiceInvalidCurrencyError,
    ServiceTransactionNotFoundError,
    ServiceUserNotFoundError,
    TransactionNotFoundException,
    UserNotFoundException,
)
from core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from core.services.transaction_service import TransactionService
from infrastructure.dependencies import get_uow

router = APIRouter(prefix="/transactions", tags=["Transactions"])
transaction_service = TransactionService()


class TransactionResponse(BaseModel):
    transactions: list[TransactionOut]
    is_valid: bool


class SummaryResponse(BaseModel):
    summary: dict[str, dict[str, dict[str, float]]]
    is_valid: bool


@router.post("/", status_code=201, response_model=None)
def add_transaction(
    transaction: list[TransactionIn] | TransactionIn,
    id_user: int = Depends(get_id_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> dict[str, str]:
    """Adds a new transaction."""

    try:
        transaction_service.add_transaction(uow, id_user, transaction)
        return {"message": "Transaction created successfully."}

    except ServiceInvalidCurrencyError:
        raise InvalidCurrencyException()
    except ServiceUserNotFoundError:
        raise UserNotFoundException()
    except ServiceCategoryNotFoundError:
        raise CategoryNotFoundException()
    except ServiceError:
        raise InternalServerErrorException()


@router.get("/", response_model=TransactionResponse)
def get_transactions(
    begin_date: date | None = None,
    end_date: date | None = None,
    to_currency: str | None = None,
    tr_type: Literal["income", "expense"] | None = None,
    primary: str | None = None,
    secondary: str | None = None,
    order: Literal["name", "date", "value", "currency", "primary", "secondary"] | None = None,
    order_dir: Literal["ASC", "DESC"] = "ASC",
    limit: int | None = None,
    offset: int = 0,
    name: str | None = None,
    id_user: int = Depends(get_id_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> TransactionResponse:
    """
    Retrieves transactions based on specified filters.
    """

    try:
        transactions, is_valid = transaction_service.get_transaction(
            uow,
            id_user,
            begin_date,
            end_date,
            to_currency,
            tr_type,
            primary,
            secondary,
            order,
            order_dir,
            limit,
            offset,
            name,
        )

        return TransactionResponse(transactions=transactions, is_valid=is_valid)

    except ServiceInvalidCurrencyError:
        raise InvalidCurrencyException()
    except OperationNotPermittedError:
        raise BadRequestException()
    except ServiceError:
        raise InternalServerErrorException()


@router.get("/summary/", response_model=SummaryResponse)
def get_summary(
    to_currency: str,
    tr_type: Literal["income", "expense"],
    begin_date: date | None = None,
    end_date: date | None = None,
    primary: str | None = None,
    secondary: str | None = None,
    id_user: int = Depends(get_id_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> SummaryResponse:
    """
    Retrieves a summary of transactions.
    """
    try:
        summary, is_valid = transaction_service.get_summary(
            uow,
            id_user,
            begin_date,
            end_date,
            tr_type,
            to_currency,
            primary,
            secondary,
        )
        return SummaryResponse(summary=summary, is_valid=is_valid)

    except ServiceInvalidCurrencyError:
        raise InvalidCurrencyException()
    except (ServiceError, ServiceExchangeRateNotFoundError):
        raise InternalServerErrorException()


@router.put("/{id_tr}", status_code=204, response_model=None)
def edit_transaction(
    id_tr: int,
    new_tr: TransactionIn,
    id_user: int = Depends(get_id_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> dict[str, str]:
    """
    Edits an existing transaction.
    """
    try:
        transaction_service.edit_transaction(uow, id_tr, new_tr, id_user)
        return {"message": "Transaction edited successfully."}

    except ServiceInvalidCurrencyError:
        raise InvalidCurrencyException()
    except ServiceTransactionNotFoundError:
        raise TransactionNotFoundException()
    except ServiceCategoryNotFoundError:
        raise CategoryNotFoundException()
    except OperationNotPermittedError:
        raise ForbiddenException()
    except ServiceError:
        raise InternalServerErrorException()


@router.delete("/{id_tr}", status_code=204, response_model=None)
def delete_transaction(
    id_tr: int,
    id_user: int = Depends(get_id_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> dict[str, str]:
    """
    Deletes a transaction.
    """
    try:
        transaction_service.delete_transaction(uow, id_tr, id_user)
        return {"message": "Transaction deleted successfully."}

    except ServiceTransactionNotFoundError:
        raise TransactionNotFoundException()
    except OperationNotPermittedError:
        raise ForbiddenException()
    except ServiceError:
        raise InternalServerErrorException()
