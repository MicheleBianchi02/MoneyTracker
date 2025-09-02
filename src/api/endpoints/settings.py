from fastapi import APIRouter, Body, Depends

from src.core.domain.setting import Setting
from src.core.exceptions import (
    BadRequestException,
    CurrencyNotFoundError,
    DuplicateCurrencyException,
    InternalServerErrorException,
    ServiceDuplicateCurrencyError,
    ServiceError,
    ServiceSettingNotFoundError,
    SettingNotFoundException,
)
from src.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from src.core.services.user_setting_service import UserSettingService
from src.infrastructure.dependencies import get_uow
from src.infrastructure.job_manager import COMPLETED_CODE, FAILED_CODE, UNKNOWN_CODE, check_status

router = APIRouter(prefix="/settings", tags=["Settings"])
setting_service = UserSettingService()


@router.post("/", status_code=204)
def add_or_update_setting(
    id_user: int = Body(...),
    setting_name: str = Body(...),
    value: int | float | str | bool = Body(...),
    wait_response: bool = True,
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Adds or updates a user-specific setting.
    """
    try:
        job_id = setting_service.add(uow, id_user, setting_name, value)

        if wait_response:
            status, _ = check_status(job_id)

            if status == COMPLETED_CODE:
                return {"message": "Setting added successfully."}
            elif status == FAILED_CODE or status == UNKNOWN_CODE:
                raise InternalServerErrorException()

        else:
            return job_id

    except ServiceSettingNotFoundError:
        raise SettingNotFoundException()
    except ServiceError:
        raise BadRequestException()
    except Exception:
        raise InternalServerErrorException()


@router.get("/", response_model=list[Setting])
def get_settings(
    id_user: int | None = None,
    setting_name: str | None = None,
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Retrieves settings.
    """
    try:
        return setting_service.get(uow, id_user, setting_name)
    except ServiceError:
        raise BadRequestException()
    except Exception:
        raise InternalServerErrorException()


@router.post("/currencies/", status_code=204)
def add_currency(
    id_user: int = Body(...),
    currency_code: str = Body(...),
    currency_symbol: str | None = Body(None),
    wait_response: bool = True,
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Adds a currency for a user.
    """
    try:
        job_id = setting_service.add_currency(uow, id_user, currency_code, currency_symbol)
        if wait_response:
            status, _ = check_status(job_id)

            if status == COMPLETED_CODE:
                return {"message": "Setting edited successfully."}
            elif status == FAILED_CODE or status == UNKNOWN_CODE:
                raise InternalServerErrorException()

        else:
            return job_id

    except ServiceDuplicateCurrencyError:
        raise DuplicateCurrencyException()
    except ServiceError:
        raise BadRequestException()
    except Exception:
        raise InternalServerErrorException()


@router.get("/currencies/", response_model=list[tuple[str, str | None]])
def get_currencies(id_user: int | None, uow: AbstractUnitOfWork = Depends(get_uow)):
    """
    Retrieves all currencies for a user.
    """
    try:
        return setting_service.get_currency_list(uow, id_user)
    except ServiceError:
        raise BadRequestException()
    except Exception:
        raise InternalServerErrorException()


@router.delete("/currencies/", status_code=204)
def delete_currency(
    id_user: int = Body(...),
    currency_code: str = Body(...),
    wait_response: bool = True,
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Deletes a currency for a user.
    """
    try:
        job_id = setting_service.delete_currency(uow, id_user, currency_code)
        if wait_response:
            status, _ = check_status(job_id)

            if status == COMPLETED_CODE:
                return {"message": "Setting deleted successfully."}
            elif status == FAILED_CODE or status == UNKNOWN_CODE:
                raise InternalServerErrorException()

        else:
            return job_id
    except CurrencyNotFoundError:
        raise BadRequestException()
    except ServiceError:
        raise BadRequestException()
    except Exception:
        raise InternalServerErrorException()
