import logging

from moneytracker.core.domain.exchange_rate import Currency
from moneytracker.core.exceptions import RepositoryError, ServiceError
from moneytracker.infrastructure.sqlite.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


class AppSettingService:
    def get_currencies(
        self,
        uow: UnitOfWork,
        is_active: bool | None = None,
    ) -> list[Currency]:
        logger.debug(f"Getting default currency list with is_active:{is_active}")

        try:
            with uow:
                return uow.app_setting.get_currency_list(is_active)

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e
