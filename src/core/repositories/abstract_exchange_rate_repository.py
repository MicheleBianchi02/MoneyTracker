from abc import ABC, abstractmethod
from datetime import date

from src.core.domain.exchange_rate import ExchangeRate


class AbstractExchangeRateRepository(ABC):
    """Database function relative to exchage rates.

    Method
    ------
        - add : Add a list of exchenge rete to the database
        - get : Get a list of exchange rate for the given date
        - get_closest : Get a list of exchange rates with a date's parameter closest to
            the given date
        - get_not_updated : Get a list of exchange rates with the is_updated's parameter
            False
        - edit : Edit an exchange rate present in the database
        - delete : Delete an exchange rate present in the database

    """

    @abstractmethod
    def add(self, exc_list: list[ExchangeRate] | ExchangeRate) -> None:
        """Add exchange rates to the database.

        Parameters
        ----------
            - exc_list (list or ExchangeRate) : List containing all the Exchange Rates
                that need to be saved in the database.
                The argument can also be a single ExchangeRate (not a list).

        Raises
        ------
            - DuplicateEntityError: If that exchange rate is already present in db.
            - RepositoryError: If something went wrong with the database

        Notes
        -----
            ExchangeRate are considered unique in the db if
                (from_currency, to_currency, rate_date) are unique.
            All those value at once need to be unique, not the single values.
        """

        raise NotImplementedError

    @abstractmethod
    def get(
        self,
        exc_date: date,
        from_currency: str | None = None,
        to_currency: str | None = None,
    ) -> list[ExchangeRate]:
        """Get the exchange rate for the given date.

        Parameters
        ----------
            - date (datetime.date) : required date
            - from_currency (str or None) : currency from which to convert. If None, all
                the exchange rate are returned. The default value is None.
            - to_curency (str or None) :

        Returns
        -------
            A list of all the exchange rate for the given date.
            The length of the list is the same as the number of currencies saved in the
            database.

        Raises
        ------
            RepositoryError: If something went wrong with the database
        """

        raise NotImplementedError

    @abstractmethod
    def get_closest(self, date: date) -> list[ExchangeRate]:
        """Get the exchange rates closest to the given date.

        Parameters
        ----------
            - date (datetime.date) : required date

        Returns
        -------
            List of Exchange Rates with the date closest to the the given one.
            All the returned exchange rates will have the same date but a different
            currency. The list will be empty if the db is empty.

        Raises
        ------
            RepositoryError: If something went wrong with the database

        Notes
        -----
            Can be used when an exchange rate is to be added to the db but the value is
            unknown (for istance when there is not internet connection). In this way in
            the database are still saved reasonable values (and so the UI will display
            fair values).
        """

        raise NotImplementedError

    @abstractmethod
    def get_not_updated(
        self,
        begin_date: date | None,
        end_date: date | None,
    ) -> list[ExchangeRate]:
        """Get all the non updated exchange rates in the given date range.

        Parameters
        ----------
            - begin_date (datetime.date or None) : starting date of the date range.
                If None there is no inferior limit (all exchange rate up to end_date)
            - end_date (datetime.date or None) : ending date of the date range.
                If None there is no superior limit (all exchange rate from starting date).

        Returns
        -------
            List of all the exchange rates with the is_updated parameter False. Those
            exchange rates can have different dates and currencies.

        Raises
        ------
            RepositoryError: If something went wrong with the database

        """

        raise NotImplementedError

    @abstractmethod
    def get_missing_rates_dates(self, date_list: list[date] | date) -> list[date]:
        """Get dates wiht missing exchange rates.

        Parameters
        ----------
            date_list (list or date) : date for which it is necessary to check whether
                exchange rates are present in the database. Dates in date_list doesn't
                need to be unique (the list can contain duplicate dates).

        Returns
        -------
            A list containing all the dates (present in date_list) that have missing
            exchange rates in the db.
        """

        raise NotImplementedError

    @abstractmethod
    def edit(self, new_exch: ExchangeRate) -> None:
        """Edit the given exchange rate.

        The only parameter that can be changed are:
            rate;
            is_updated

        from_currency, to_currency and rate_date can't be changed.

        Parameters
        ----------
            - new_exc (ExchangeRate) : ExchageRate with the new updated values.
                Important: the from_currency, to_currency and rate_date values must be
                the same of exchange_rate to be edited.

        Raises
        ------
            - EntityNotFounError: If the given exchange rate is not in the db.
            - RepositoryError: If something went wrong with the database

        """

        raise NotImplementedError

    @abstractmethod
    def delete(self, exc: ExchangeRate) -> None:
        """Delete the exchange rate with the given id.

        Parameters
        ----------
            - exc (ExchangeRate) : exchange rate to be deleted. Only the from_currency,
                to_currency and exc_date parameters must be the correct one.

        Raises
        ------
            - EntityNotFounError: If the given exchange rate is not in the db.
            - RepositoryError: If something went wrong with the database
        """

        raise NotImplementedError
