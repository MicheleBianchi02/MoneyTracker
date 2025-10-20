from fastapi import APIRouter, Body, Depends

from moneytracker.api.dependencies import get_id_user
from moneytracker.core.domain.exchange_rate import Currency
from moneytracker.core.domain.setting import Setting
from moneytracker.core.exceptions import (
    BadRequestException,
    CurrencyNotFoundError,
    DuplicateCurrencyException,
    InternalServerErrorException,
    InvalidCurrencyException,
    ServiceDuplicateCurrencyError,
    ServiceError,
    ServiceInvalidCurrencyError,
    ServiceSettingNotFoundError,
    SettingNotFoundException,
)
from moneytracker.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from moneytracker.core.services.user_setting_service import UserSettingService
from moneytracker.infrastructure.dependencies import get_uow

router = APIRouter(prefix="/settings", tags=["Settings"])
setting_service = UserSettingService()


@router.post("/", status_code=204)
def add_or_update_setting(
    setting_name: str = Body(...),
    value: int | float | str | bool = Body(...),
    id_user: int = Depends(get_id_user),
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
    except ServiceError:
        raise InternalServerErrorException()


@router.get("/default/", response_model=list[Setting])
def get_default_settings(
    setting_name: str | None = None,
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Retrieves default settings.
    """
    try:
        return setting_service.get(uow, None, setting_name)

    except ServiceError:
        raise InternalServerErrorException()


@router.get("/", response_model=list[Setting])
def get_settings(
    setting_name: str | None = None,
    id_user=Depends(get_id_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Retrieves user specific settings.
    """
    try:
        return setting_service.get(uow, id_user, setting_name)

    except ServiceError:
        raise InternalServerErrorException()


@router.post("/currencies/", status_code=204)
def add_currency(
    currency_code: str = Body(...),
    id_user: int = Depends(get_id_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Adds a currency for a user.
    """
    try:
        setting_service.add_currency(uow, id_user, currency_code)
        return {"message": "Setting edited successfully."}

    except ServiceInvalidCurrencyError:
        raise InvalidCurrencyException()
    except ServiceDuplicateCurrencyError:
        raise DuplicateCurrencyException()
    except ServiceError:
        raise InternalServerErrorException()


@router.get("/currencies/available/", response_model=list[Currency])
def get_available_currencies(
    is_active: bool | None = None,
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Retrieves all available currencies.
    """
    try:
        currencies = setting_service.get_currency_list(uow, None, is_active=is_active)
        return currencies or []

    except ServiceError:
        raise InternalServerErrorException()


@router.get("/currencies/", response_model=list[Currency])
def get_currencies(
    is_active: bool | None = None,
    id_user: int = Depends(get_id_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Retrieves all currencies for a user.
    """
    try:
        currencies = setting_service.get_currency_list(uow, id_user, is_active=is_active)
        return currencies or []

    except ServiceError:
        raise InternalServerErrorException()


@router.delete("/currencies/", status_code=204)
def delete_currency(
    currency_code: str,
    id_user: int = Depends(get_id_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Deletes a user currency.
    """
    try:
        setting_service.delete_currency(uow, id_user, currency_code)
        return {"message": "Setting deleted successfully."}
    except CurrencyNotFoundError:
        raise BadRequestException()
    except ServiceError:
        raise InternalServerErrorException()
