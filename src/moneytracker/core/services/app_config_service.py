import logging

from moneytracker.core.domain.exchange_rate import Currency
from moneytracker.core.exceptions import RepositoryError, ServiceError
from moneytracker.core.repositories.abstract_unit_of_work import AbstractUnitOfWork

logger = logging.getLogger(__name__)


class AppConfigService:
    def get_currencies(
        self,
        uow: AbstractUnitOfWork,
        is_active: bool | None = None,
    ) -> list[Currency]:
        logger.info(f"Getting default currency list with is_active:{is_active}")

        try:
            with uow:
                return uow.app_config.get_currency_list(is_active)

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e
