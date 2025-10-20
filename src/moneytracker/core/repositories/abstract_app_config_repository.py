from abc import ABC, abstractmethod

from moneytracker.core.domain.exchange_rate import Currency


class AbstractAppConfigRepository(ABC):
    @abstractmethod
    def add(self, name: str, value: str) -> None:
        """Add app specific configuration paramter to the database.

        Parameters
        ----------
            - name (str) : name of the config paramter
            - value (str) : value of that parameter. It must be a string, so the
                conversion must happen before calling this method.

        Raises
        ------
            - DuplicateEntityError: If Unique constraint error occour (e.g. two identical
                name are inserted)
            - RepositoryError: If something went wrong with the database
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, name: str) -> str | None:
        """Get app specific config parameter with the given name.

        Parameters
        ----------
            - name (str) : name of the required config paramter

        Returns
        -------
            The value of the required paramter. The type is str.
            None is returned if the config paramater with that name doesn't exist in the
            database.

        Raises
        ------
            - RepositoryError: If something went wrong with the database
        """

        raise NotImplementedError

    @abstractmethod
    def edit(self, name: str, new_value: str) -> None:
        """Edit the app specific config paramter with the given name

        Parameters
        ----------
            - name (str) : name of the config paramter
            - new_value (str) : updated value of that parameter. It must be a string, so
                the conversion must happen before calling this method.

        Raises
        ------
            - EntityNotFounError: If the given app config's name is not in the db.
            - RepositoryError: If something went wrong with the database
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, name: str) -> None:
        """Delete the app specific config paramter with the given name

        Parameters
        ----------
            - name (str) : name of the config paramter

        Raises
        ------
            - EntityNotFounError: If the given app config's name is not in the db.
            - RepositoryError: If something went wrong with the database
        """
        raise NotImplementedError

    @abstractmethod
    def add_upd_currency_list(self, currency_list: list[Currency]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_currency_list(self, is_active: bool | None = None) -> list[Currency]:
        raise NotImplementedError
