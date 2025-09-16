import logging
import uuid

from src.core.domain.setting import Setting
from src.core.exceptions import (
    CurrencyNotFoundError,
    RepositoryError,
    ServiceDuplicateCurrencyError,
    ServiceError,
    ServiceInvalidCurrencyError,
    ServiceSettingNotFoundError,
)
from src.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from src.core.services.exc_rate_service import exc_rate_service
from src.infrastructure.job_manager import FAILED_CODE, UNKNOWN_CODE, check_status, job_manager
from src.infrastructure.task_queue import task_queue
from src.infrastructure.worker import (
    ADD_CURRENCY_TASK_NAME,
    ADD_SETTING_TASK_NAME,
    DELETE_CURRENCY_TASK_NAME,
)

logger = logging.getLogger(__name__)


class UserSettingService:
    def add(
        self,
        uow: AbstractUnitOfWork,
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

        job_id = str(uuid.uuid4())
        try:
            with uow:
                setting = uow.user_setting.get(None, setting_name)

            if not setting:
                logger.error(f"Setting with name:{setting_name} not present in the database")
                raise ServiceSettingNotFoundError("Setting not found")

            job_manager.add_job(job_id)

            args = (id_user, setting_name, value)
            task_queue.put((ADD_SETTING_TASK_NAME, job_id, args), block=True)

            status, result = check_status(job_id)
            if status == FAILED_CODE or status == UNKNOWN_CODE:
                logger.error(f"Worker failed - job_status:{status} - job_id:{job_id}")
                raise ServiceError(f"Service error - job_status:{status} ")

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def get(
        self,
        uow: AbstractUnitOfWork,
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
        uow: AbstractUnitOfWork,
        id_user: int,
        currency_code: str,
        currency_symbol: str | None,
    ) -> str:
        """Add user specific currency to the database.

        Parameters
        ----------
            - id_user (int) : id of the user
            - currency_code (str) : code of the currency. It should be composed of 3
                characters (e.g. 'EUR', 'USD').
            - currency_symbol (str or None) : symbol of the currency (e.g. '$', '€'). If
                None no symbol is saved in the database.

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

        logger.info(
            f"Adding currency {currency_code} with symbol {currency_symbol} "
            f"to the user with id_user {id_user}"
        )

        job_id = str(uuid.uuid4())
        try:
            with uow:
                curr_list = uow.user_setting.get_currency_list(id_user)

            if currency_code in curr_list:
                logger.error(
                    f"The currency: {currency_code} is already present for the user with id_user: {id_user}"
                )
                raise ServiceDuplicateCurrencyError(
                    f"The currency: {currency_code} is already present for the user with id_user: {id_user}"
                )

            currency_code = currency_code.upper()
            if not exc_rate_service.validate_currency(currency_code):
                logger.error(f"{currency_code} is not a valid currency")
                raise ServiceInvalidCurrencyError()

            job_manager.add_job(job_id)

            args = (id_user, currency_code, currency_symbol)
            task_queue.put((ADD_CURRENCY_TASK_NAME, job_id, args), block=True)

            status, result = check_status(job_id)
            if status == FAILED_CODE or status == UNKNOWN_CODE:
                logger.error(f"Worker failed - job_status:{status} - job_id:{job_id}")
                raise ServiceError(f"Service error - job_status:{status} ")

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def get_currency_list(
        self, uow: AbstractUnitOfWork, id_user: int | None
    ) -> list[tuple[str, str]]:
        """Get user specific currency from the database.

        Parameters
        ----------
            - id_user (int or None) : id of the user. If None, the available currencies
                is returned.

        Returns
        -------
            A list of all currencies pertaining to that user.
            The format is: [ (currency_code_1, symbol_1), (currency_code_2, symbol_2)... ]
            An example is:
                [("USD", "$"), ("EUR", "€"), ("CAD", None), ("GBP", "£"), ("NZD", None)]
            If the currency has no symbol, None is returned.

        Raises
        ------
            ServiceError: If something went wrong with the repository or the service.
        """

        logger.info(f"Getting currency list for user with id_user: {id_user}")

        try:
            if id_user is not None:
                with uow:
                    return uow.user_setting.get_currency_list(id_user)

            return exc_rate_service.available_currencies_detailed

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def delete_currency(self, uow: AbstractUnitOfWork, id_user: int, currency_code: str) -> None:
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
        job_id = str(uuid.uuid4())

        try:
            with uow:
                curr_list = uow.user_setting.get_currency_list(id_user)

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

            job_manager.add_job(job_id)

            args = (id_user, currency_code)
            task_queue.put((DELETE_CURRENCY_TASK_NAME, job_id, args), block=True)

            status, result = check_status(job_id)
            if status == FAILED_CODE or status == UNKNOWN_CODE:
                logger.error(f"Worker failed - job_status:{status} - job_id:{job_id}")
                raise ServiceError(f"Service error - job_status:{status} ")

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e
