from fastapi import APIRouter, Body, Depends

from src.core.domain.setting import Setting
from src.core.exceptions import (
    BadRequestException,
    CurrencyNotFoundError,
    DuplicateCurrencyException,
    ServiceDuplicateCurrencyError,
    ServiceError,
    ServiceSettingNotFoundError,
    ServiceUserNotFoundError,
    SettingNotFoundException,
    UserNotFoundException,
)
from src.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from src.core.services.user_setting_service import UserSettingService
from src.infrastructure.dependencies import get_uow

router = APIRouter(prefix="/settings", tags=["Settings"])
setting_service = UserSettingService()


@router.post("/", status_code=204)
def add_or_update_setting(
    id_user: int = Body(...),
    setting_name: str = Body(...),
    value: int | float | str | bool = Body(...),
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Adds or updates a user-specific setting.
    """
    try:
        setting_service.add(uow, id_user, setting_name, value)
        return {"message": "Setting added successfully."}

    except ServiceSettingNotFoundError:
        raise SettingNotFoundException()
    except ServiceError as e:
        raise BadRequestException(str(e))


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
    except ServiceError as e:
        raise BadRequestException(str(e))


@router.post("/currencies/", status_code=204)
def add_currency(
    id_user: int = Body(...),
    currency_code: str = Body(...),
    currency_symbol: str | None = Body(None),
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Adds a currency for a user.
    """
    try:
        setting_service.add_currency(uow, id_user, currency_code, currency_symbol)
        return
    except ServiceUserNotFoundError:
        raise UserNotFoundException()
    except ServiceDuplicateCurrencyError as e:
        raise DuplicateCurrencyException(str(e))
    except ServiceError as e:
        raise BadRequestException(str(e))


@router.get("/currencies/", response_model=list[tuple[str, str | None]])
def get_currencies(id_user: int | None, uow: AbstractUnitOfWork = Depends(get_uow)):
    """
    Retrieves all currencies for a user.
    """
    try:
        return setting_service.get_currency_list(uow, id_user)
    except ServiceError as e:
        raise BadRequestException(str(e))


@router.delete("/currencies/", status_code=204)
def delete_currency(
    id_user: int = Body(...),
    currency_code: str = Body(...),
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Deletes a currency for a user.
    """
    try:
        setting_service.delete_currency(uow, id_user, currency_code)
        return
    except CurrencyNotFoundError as e:
        raise BadRequestException(str(e))
    except ServiceError as e:
        raise BadRequestException(str(e))
