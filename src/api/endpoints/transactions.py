from datetime import date

from fastapi import APIRouter, Depends, Query

from src.core.domain.transaction import TransactionIn, TransactionOut
from src.core.exceptions import (
    BadRequestException,
    CategoryNotFoundException,
    ServiceCategoryNotFoundError,
    ServiceError,
    ServiceTransactionNotFoundError,
    ServiceUserNotFoundError,
    TransactionNotFoundException,
    UserNotFoundException,
)
from src.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from src.core.services.transaction_service import TransactionService
from src.infrastructure.dependencies import get_uow

router = APIRouter(prefix="/transactions", tags=["Transactions"])
transaction_service = TransactionService()


@router.post("/", status_code=201, response_model=None)
def add_transaction(
    transaction: TransactionIn,
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Adds a new transaction.
    """
    try:
        transaction_service.add_transaction(uow, transaction)
        return {"message": "Transaction added successfully."}
    except ServiceUserNotFoundError:
        raise UserNotFoundException()
    except ServiceCategoryNotFoundError:
        raise CategoryNotFoundException()
    except ServiceError as e:
        raise BadRequestException(str(e))


@router.get("/", response_model=list[TransactionOut])
def get_transactions(
    id_user: int,
    begin_date: date | None = None,
    end_date: date | None = None,
    tr_type: str | None = Query(None, pattern="^(income|expense)$"),
    primary: str | None = None,
    secondary: str | None = None,
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Retrieves transactions based on specified filters.
    """
    try:
        return transaction_service.get_transaction(
            uow,
            id_user,
            begin_date,
            end_date,
            tr_type,
            primary,
            secondary,
        )
    except ServiceError as e:
        raise BadRequestException(str(e))


@router.get("/summary/")
def get_summary(
    id_user: int,
    to_currency: str,
    tr_type: str = Query(..., pattern="^(income|expense)$"),
    begin_date: date | None = None,
    end_date: date | None = None,
    primary: str | None = None,
    secondary: str | None = None,
    uow: AbstractUnitOfWork = Depends(get_uow),
):
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
        return {"summary": summary, "is_valid": is_valid}

    except ServiceError as e:
        raise BadRequestException(str(e))


@router.put("/{id_tr}", status_code=204)
def edit_transaction(
    id_tr: int,
    new_tr: list[TransactionIn] | TransactionIn,
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Edits an existing transaction.
    """
    try:
        transaction_service.edit_transaction(uow, id_tr, new_tr)
        return
    except ServiceTransactionNotFoundError:
        raise TransactionNotFoundException()
    except ServiceCategoryNotFoundError:
        raise CategoryNotFoundException()
    except ServiceError as e:
        raise BadRequestException(str(e))


@router.delete("/{id_tr}", status_code=204)
def delete_transaction(id_tr: int, uow: AbstractUnitOfWork = Depends(get_uow)):
    """
    Deletes a transaction.
    """
    try:
        transaction_service.delete_transaction(uow, id_tr)
        return
    except ServiceTransactionNotFoundError:
        raise TransactionNotFoundException()
    except ServiceError as e:
        raise BadRequestException(str(e))
