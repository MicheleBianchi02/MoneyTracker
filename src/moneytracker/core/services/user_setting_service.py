import logging

from moneytracker.core.domain.exchange_rate import Currency
from moneytracker.core.domain.setting import Setting
from moneytracker.core.exceptions import (
    CurrencyNotFoundError,
    RepositoryError,
    ServiceDuplicateCurrencyError,
    ServiceError,
    ServiceInvalidCurrencyError,
    ServiceSettingNotFoundError,
)
from moneytracker.core.services.exc_rate_service import ExchangeRateService
from moneytracker.infrastructure.job_manager import complete_task
from moneytracker.infrastructure.sqlite.unit_of_work import UnitOfWork
from moneytracker.infrastructure.worker import (
    ADD_SETTING_TASK_NAME,
    ADD_USER_CURRENCY_TASK_NAME,
    DELETE_USER_CURRENCY_TASK_NAME,
)

logger = logging.getLogger(__name__)


class UserSettingService:
    def add(
        self,
        uow: UnitOfWork,
        id_user: int,
        setting_name: str,
        value: int | float | str | bool,
    ) -> None:
        """Add or update user specific setting in the database.

        Parameters
        ----------
            - id_user (int) : id of the user
            - setting_name (str) : setting name
            - value (int or float or str or bool) : value of the setting. The type should
                match the one of the setting (the data_type column in the db's table).
                If the setting is constrained, the value is the item_value of the allowed
                setting, that should be inside the relative table.

        Raises
        ------
            - ServiceSettingNotFoundError: If the setting, with the given setting_name, or the
                allowed_setting (if the setting is constrained) are not found in the db.
            - ServiceError: If something went wrong with the repository or the service.
        """

        logging.info(
            f"Adding user setting with name {setting_name} for user with id_user: {id_user}"
        )

        try:
            with uow:
                setting = uow.user_setting.get(None, setting_name)

            if not setting:
                logger.error(f"Setting with name:{setting_name} not present in the database")
                raise ServiceSettingNotFoundError("Setting not found")

            args = (id_user, setting_name, value)
            complete_task(ADD_SETTING_TASK_NAME, args)

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def get(
        self,
        uow: UnitOfWork,
        id_user: int | None,
        setting_name: str | None = None,
    ) -> list[Setting]:
        """Get settings from the database

        Parameters
        ----------
            - id_user (int or None) : id of the user. If None, the returned value (key
                of Setting instance) is the setting's default value. This happen also
                when the id_user is not present in the table.
            - setting_name (str or None) : setting_name to search for. If None, all
                settings are returned. The default value is None.

        Returns
        -------
            A list containing all the settings (instances of Setting).
            A list is still returned if only one setting (or no one) is found.

        Raises
        ------
            ServiceError: If something went wrong with the repository or the service.
        """

        logger.info(
            f"Getting user settings with name {setting_name} for user with id_user: {id_user}"
        )

        try:
            with uow:
                return uow.user_setting.get(id_user, setting_name)

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def add_currency(
        self,
        uow: UnitOfWork,
        id_user: int,
        currency_code: str,
    ) -> str:
        """Add user specific currency to the database.

        Parameters
        ----------
            - id_user (int) : id of the user
            - currency_code (str) : code of the currency. It should be composed of 3
                characters (e.g. 'EUR', 'USD').

        Returns
        -------
            The corresponding job_id. At the beginning the job_status will be pending.
            When the worker thread finished the operation, the job status get updated.

        Raises
        ------
            - ServiceInvalidCurrencyError: If the provided currency code is not valid.
            - ServiceDuplicateCurrencyError: If trying to add an already present (for that
                user) currency code.
            - ServiceError: If something went wrong with the repository or the service.

        Notes
        -----
            User specific currencies are considered unique if (id_user, currency_code)
            are equal, indipendently on the symbol.
        """

        currency_code = currency_code.upper()

        logger.info(f"Adding currency {currency_code} to the user with id_user:{id_user}")

        try:
            user_currencies = self.get_currency_list(uow, id_user, is_active=None)
            user_currencies = [curr.code for curr in user_currencies]

            if currency_code in user_currencies:
                logger.error(
                    f"The currency: {currency_code} is already present for the user with id_user: {id_user}"
                )
                raise ServiceDuplicateCurrencyError(
                    f"The currency: {currency_code} is already present for the user with id_user: {id_user}"
                )

            if not ExchangeRateService().validate_currency(currency_code):
                logger.error(f"{currency_code} is not a valid currency")
                raise ServiceInvalidCurrencyError()

            args = (id_user, currency_code)
            complete_task(ADD_USER_CURRENCY_TASK_NAME, args)

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def get_currency_list(
        self, uow: UnitOfWork, id_user: int | None, is_active: bool | None = None
    ) -> list[Currency]:
        """Get user specific currency from the database.

        Parameters
        ----------
            - id_user (int or None) : id of the user. If None, the available currencies
                is returned.
            - is_active (bool or None) : if True, only active currencies are returned,
                if False, only deprecated currencies are returned. If None, all
                currencies are returned.

        Returns
        -------
            A list of all currencies pertaining to that user.

        Raises
        ------
            ServiceError: If something went wrong with the repository or the service.
        """

        logger.info(f"Getting currency list for user with id_user: {id_user}")

        try:
            if id_user is not None:
                with uow:
                    return uow.user_setting.get_user_currency(id_user, is_active=is_active)

            exc_rate_service = ExchangeRateService()
            if is_active is None:
                active = exc_rate_service.active_currencies_detailed
                non_active = exc_rate_service.non_active_currencies_detailed

                currencies = []
                currencies.extend(active)
                currencies.extend(non_active)

                return currencies

            elif is_active:
                return exc_rate_service.active_currencies_detailed
            elif not is_active:
                return exc_rate_service.non_active_currencies_detailed

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def delete_currency(self, uow: UnitOfWork, id_user: int, currency_code: str) -> None:
        """Delete user specific currency from the database.

        Parameters
        ----------
            - id_user (int) : id of the user
            - currency_code (str) : currency to be deleted.

        Raises
        ------
            - CurrencyNotFoundError: If the currency with the given id_user and currency_code
                is not in the db.
            - RepositoryError: If something went wrong with the database
        """

        logger.info(f"Deleting curerncy: {currency_code} for user with id_user: {id_user}")

        try:
            with uow:
                curr_list = uow.user_setting.get_user_currency(id_user)
            curr_list = [curr.code for curr in curr_list]

            currency_code = currency_code.upper()

            if currency_code not in curr_list:
                logger.error(
                    f"The currency: {currency_code} is not present in the database "
                    "for the user with id_user: {id_user}"
                )
                raise CurrencyNotFoundError(
                    f"The currency: {currency_code} is not present in the database "
                    "for the user with id_user: {id_user}"
                )

            args = (id_user, currency_code)
            complete_task(DELETE_USER_CURRENCY_TASK_NAME, args)

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e
