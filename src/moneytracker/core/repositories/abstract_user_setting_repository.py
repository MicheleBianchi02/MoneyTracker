from abc import ABC, abstractmethod

from moneytracker.core.domain.exchange_rate import Currency
from moneytracker.core.domain.setting import Setting


class AbstractUserSettingRepository(ABC):
    @abstractmethod
    def add(
        self,
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
            - EntityNotFoundError: If the setting, with the given setting_name, or the
                allowed_setting (if the setting is constrained) are not found in the db.
            - ForeignKeyError: If a foreign key error occour (e.g. a setting with
                a non existing id_user is added).
            - RepositoryError: If something went wrong with the database
        """

        raise NotImplementedError

    @abstractmethod
    def get(self, id_user: int | None, setting_name: str | None = None) -> list[Setting]:
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
            RepositoryError: If something went wrong with the database
        """

        raise NotImplementedError

    @abstractmethod
    def add_user_currency(
        self,
        id_user: int,
        currency_code: str,
    ) -> None:
        """Add user specific currency to the database.

        Parameters
        ----------
            - id_user (int) : id of the user
            - currency_code (str) : code of the currency. It should be composed of 3
                characters (e.g. 'EUR', 'USD').

        Raises
        ------
            - ForeignKeyError: If a foreign key error occour (e.g. a user_setting with
                a non existing id_user is added).
            - DuplicateEntityError: If Unique constraint error occour (e.g. two identical
                currencies are inserted)
            - RepositoryError: If something went wrong with the database

        Notes
        -----
            User specific currencies are considered unique if (id_user, currency_code)
            are equal, indipendently on the symbol.
        """

        raise NotImplementedError

    @abstractmethod
    def get_user_currency(self, id_user: int, is_active=bool | None) -> list[Currency]:
        """Get user specific currency from the database.

        Parameters
        ----------
            - id_user (int) : id of the user.
            - is_active (bool or None) : If True, return only active currencies
                (not deprecated one), if False, return only deprecated currencies.
                If None, return all currencies indipendently if they are active or not.

        Returns
        -------
            A list of all currencies (Currency instances) pertaining to that user.

        Raises
        ------
            RepositoryError: If something went wrong with the database
        """

        raise NotImplementedError

    @abstractmethod
    def delete_user_currency(self, id_user: int, currency_code: str) -> None:
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

        raise NotImplementedError
