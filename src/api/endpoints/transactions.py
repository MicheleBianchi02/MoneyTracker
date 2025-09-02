from datetime import date

from fastapi import APIRouter, Depends, Query

from src.core.domain.transaction import TransactionIn, TransactionOut
from src.core.exceptions import (
    BadRequestException,
    CategoryNotFoundException,
    InternalServerErrorException,
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
from src.infrastructure.job_manager import (
    COMPLETED_CODE,
    FAILED_CODE,
    UNKNOWN_CODE,
    check_status,
)

router = APIRouter(prefix="/transactions", tags=["Transactions"])
transaction_service = TransactionService()


time_interval = 0.07  # seconds


@router.post("/", status_code=201, response_model=None)
def add_transaction(
    transaction: TransactionIn,
    wait_response: bool = True,
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> str | dict[str, str]:
    """Adds a new transaction.
    If wait_response is True nothing is returned, otherwise the job_id is returned."""

    try:
        job_id = transaction_service.add_transaction(uow, transaction)

        if wait_response:
            status, _ = check_status(job_id)

            if status == COMPLETED_CODE:
                return {"message": "Transaction added successfully."}
            elif status == FAILED_CODE or status == UNKNOWN_CODE:
                raise InternalServerErrorException()

        else:
            return job_id

    except ServiceUserNotFoundError:
        raise UserNotFoundException()
    except ServiceCategoryNotFoundError:
        raise CategoryNotFoundException()
    except ServiceError:
        raise BadRequestException()
    except Exception:
        raise InternalServerErrorException()


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
    except ServiceError:
        raise BadRequestException()
    except Exception:
        raise InternalServerErrorException()


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

    except ServiceError:
        raise BadRequestException()
    except Exception:
        raise InternalServerErrorException()


@router.put("/{id_tr}", status_code=204, response_model=None)
def edit_transaction(
    id_tr: int,
    new_tr: TransactionIn,
    wait_response: bool = True,
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> str | dict[str, str]:
    """
    Edits an existing transaction.
    """
    try:
        job_id = transaction_service.edit_transaction(uow, id_tr, new_tr)

        if wait_response:
            status, _ = check_status(job_id)

            if status == COMPLETED_CODE:
                return {"message": "Transaction edited successfully."}
            elif status == FAILED_CODE or status == UNKNOWN_CODE:
                raise InternalServerErrorException()

        else:
            return job_id

    except ServiceTransactionNotFoundError:
        raise TransactionNotFoundException()
    except ServiceCategoryNotFoundError:
        raise CategoryNotFoundException()
    except ServiceError:
        raise BadRequestException()
    except Exception:
        raise InternalServerErrorException()


@router.delete("/{id_tr}", status_code=204, response_model=None)
def delete_transaction(
    id_tr: int,
    wait_response: bool = True,
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> str | dict[str, str]:
    """
    Deletes a transaction.
    """
    try:
        job_id = transaction_service.delete_transaction(uow, id_tr)

        if wait_response:
            status, _ = check_status(job_id)

            if status == COMPLETED_CODE:
                return {"message": "Transaction deleted successfully."}
            elif status == FAILED_CODE or status == UNKNOWN_CODE:
                raise InternalServerErrorException()

        else:
            return job_id

    except ServiceTransactionNotFoundError:
        raise TransactionNotFoundException()
    except ServiceError:
        raise BadRequestException()
    except Exception:
        raise InternalServerErrorException()
