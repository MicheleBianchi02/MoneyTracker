import logging

from src.core.domain.setting import Setting
from src.core.exceptions import (
    CurrencyNotFoundError,
    DuplicateEntityError,
    EntityNotFoundError,
    ForeignKeyError,
    RepositoryError,
    ServiceDuplicateCurrencyError,
    ServiceError,
    ServiceSettingNotFoundError,
    ServiceUserNotFoundError,
)
from src.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from src.infrastructure.exchange_rate_provider.exchange_rate import ExchangeRateProvider

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
        try:
            with uow:
                uow.user_setting.add(id_user, setting_name, value)

        except EntityNotFoundError as e:
            logger.error(str(e))
            raise ServiceSettingNotFoundError("Setting not found") from e

        except (RepositoryError, Exception) as e:
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
                uow.user_setting.get(id_user, setting_name)

        except (RepositoryError, Exception) as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def add_currency(
        self,
        uow: AbstractUnitOfWork,
        id_user: int,
        currency_code: str,
        currency_symbol: str | None,
    ) -> None:
        """Add user specific currency to the database.

        Parameters
        ----------
            - id_user (int) : id of the user
            - currency_code (str) : code of the currency. It should be composed of 3
                characters (e.g. 'EUR', 'USD').
            - currency_symbol (str or None) : symbol of the currency (e.g. '$', '€'). If
                None no symbol is saved in the database.

        Raises
        ------
            - ServiceUserNotFoundError: If the provided id_user is not present in the database.
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

        try:
            with uow:
                uow.user_setting.add_currency(id_user, currency_code, currency_symbol)

        except ForeignKeyError as e:
            logger.error("The specified id_user is not present in the database")
            raise ServiceUserNotFoundError(
                "The provided id_user is not present in the database.",
            ) from e

        except DuplicateEntityError as e:
            logger.error(
                f"The currency: {currency_code} is already present for the user with id_user: {id_user}"
            )
            raise ServiceDuplicateCurrencyError(
                f"The currency: {currency_code} is already present for the user with id_user: {id_user}"
            ) from e

        except (RepositoryError, Exception) as e:
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

            return ExchangeRateProvider().available_currencies_detailed

        except (RepositoryError, Exception) as e:
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
            - EntityNotFounError: If the currency with the given id_user and currency_code
                is not in the db.
            - RepositoryError: If something went wrong with the database
        """

        logger.info(f"Deleting curerncy: {currency_code} for user with id_user: {id_user}")

        try:
            with uow:
                uow.user_setting.delete_currency(id_user, currency_code)

        except EntityNotFoundError as e:
            logger.error(
                f"Currency: {currency_code} is not present in the database for user with id: {id_user}"
            )
            raise CurrencyNotFoundError(
                f"Currency: {currency_code} is not present in the database for user with id: {id_user}"
            ) from e

        except (RepositoryError, Exception) as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e
