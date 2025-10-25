import sqlite3
import uuid
from datetime import date

from moneytracker.core.domain.exchange_rate import ExchangeRate
from moneytracker.core.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    InvalidParameterError,
    RepositoryError,
)


class ExchangeRateRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, exc_list: list[ExchangeRate] | ExchangeRate) -> None:
        """Add exchange rates to the database.

        Parameters
        ----------
            - exc_list (list or ExchangeRate) : List containing all the Exchange Rates
                that need to be saved in the database.
                The argument can also be a single ExchangeRate (not a list).

        Raises
        ------
            - InvalidParameterError: If the exchange rate provided has the same
                from_currency and to_currency parameter. This is not allowed, even if
                the rate value is 1.
            - DuplicateEntityError: If that exchange rate is already present in db.
            - RepositoryError: If something went wrong with the database

        Notes
        -----
            ExchangeRate are considered unique in the db if
                (from_currency, to_currency, rate_date) are unique.
            All those value at once need to be unique, not the single values.
        """

        if not isinstance(exc_list, list):
            # Need this because if only an ExchageRate is passed (not a list), in the
            # for we would get an error since ExchageRate is not an iteratable.
            exc_list = [exc_list]

        cursor = self._connection.cursor()

        sql = """
        INSERT INTO exchange_rates (
            from_currency,
            to_currency,
            rate,
            rate_date,
            is_updated)
        VALUES 
            (?, ?, ?, ?, ? )
        ON CONFLICT
            (from_currency, to_currency, rate_date)
        DO UPDATE SET
            rate = excluded.rate,
            is_updated = excluded.is_updated;
        """

        try:
            param_list = []
            for exc in exc_list:
                parameters = (
                    exc.from_currency,
                    exc.to_currency,
                    exc.rate,
                    exc.rate_date.isoformat(),
                    1 if exc.is_updated else 0,
                )

                param_list.append(parameters)

            cursor.executemany(sql, param_list)
            cursor.close()

        except sqlite3.DatabaseError as e:
            if "UNIQUE constraint failed" in str(e):
                raise DuplicateEntityError("Unique constrainnt error") from e

            elif "CHECK constraint failed" in str(e):
                raise InvalidParameterError(
                    "Exchange rate can't have the same from_currency and to_currency value"
                ) from e

            raise RepositoryError("Error while adding exchange rates.") from e

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

        cursor = self._connection.cursor()

        sql = """
            SELECT 
                from_currency,
                to_currency,
                rate,
                is_updated
            FROM 
                exchange_rates
            WHERE
                rate_date = ?
        """
        parameters = [exc_date.isoformat()]

        if to_currency is not None:
            sql += "AND to_currency = ?"
            parameters.append(to_currency)

        if from_currency is not None:
            sql += "AND from_currency = ?"
            parameters.append(from_currency)

        parameters = tuple(parameters)

        try:
            cursor.execute(sql, parameters)
            rate_list = cursor.fetchall()

            rate_out = []
            for rate in rate_list:
                rate_out.append(
                    ExchangeRate(
                        from_currency=rate[0],
                        to_currency=rate[1],
                        rate=rate[2],
                        rate_date=exc_date,
                        is_updated=True if rate[3] == 1 else False,
                    )
                )

            cursor.close()
            return rate_out

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                "Error while getting exchange_rates: "
                f"exc_date:{exc_date}, "
                f"from_currency:{from_currency}, "
                f"to_currency:{to_currency}. "
            ) from e

    def get_range(
        self,
        begin_date: date | None,
        end_date: date | None,
        from_currency: str | None = None,
        to_currency: str | None = None,
    ) -> list[ExchangeRate]:
        """Get the exchange rate for a given date range.

        Parameters
        ----------
            - begin_date (datetime.date or None) : starting date of the range. If None
                the lower limit is not set.
            - end_date (datetime.date or None) : end date of the range. If None, the
                upper limit is not set.
            - from_currency (str or None) : currency from which to convert. If None, all
                the exchange rate are returned. The default value is None.
            - to_curency (str or None) :

        Returns
        -------
            A list of all the exchange rate for the given range.
            The length of the list is the same as the number of currencies saved in the
            database.

        Raises
        ------
            RepositoryError: If something went wrong with the database
        """

        if begin_date is None:
            begin_date = date(1, 1, 1)

        if end_date is None:
            end_date = date(9999, 12, 31)

        begin_date = begin_date.isoformat()
        end_date = end_date.isoformat()

        cursor = self._connection.cursor()

        sql = """
            SELECT 
                from_currency,
                to_currency,
                rate_date,
                rate,
                is_updated
            FROM 
                exchange_rates
            WHERE
                rate_date BETWEEN ? AND ?
        """
        parameters = [begin_date, end_date]

        if to_currency is not None:
            sql += "AND to_currency = ?"
            parameters.append(to_currency)

        if from_currency is not None:
            sql += "AND from_currency = ?"
            parameters.append(from_currency)

        parameters = tuple(parameters)

        try:
            cursor.execute(sql, parameters)
            rate_list = cursor.fetchall()

            rate_out = []
            for rate in rate_list:
                rate_date = date.fromisoformat(rate[2])
                rate_out.append(
                    ExchangeRate(
                        from_currency=rate[0],
                        to_currency=rate[1],
                        rate=rate[3],
                        rate_date=rate_date,
                        is_updated=True if rate[4] == 1 else False,
                    )
                )

            cursor.close()
            return rate_out

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                "Error while getting exchange_rates: "
                f"begin_date:{begin_date}, "
                f"end_date:{end_date}, "
                f"from_currency:{from_currency}, "
                f"to_currency:{to_currency}. "
            ) from e

    def get_closest(self, exc_date: date) -> list[ExchangeRate]:
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

        cursor = self._connection.cursor()

        sql = """
            SELECT
                from_currency,
                to_currency,
                rate,
                rate_date,
                is_updated
            FROM
                exchange_rates
            WHERE
                rate_date = (
                    SELECT
                        rate_date
                    FROM
                        exchange_rates
                    ORDER BY
                        ABS(JULIANDAY(rate_date) - JULIANDAY(?))
                    LIMIT 1
                )        
        """

        parameters = (exc_date.isoformat(),)

        try:
            cursor.execute(sql, parameters)
            rate_get = cursor.fetchall()

            rate_list = []

            for rate in rate_get:
                rate_list.append(
                    ExchangeRate(
                        from_currency=rate[0],
                        to_currency=rate[1],
                        rate=rate[2],
                        rate_date=date.fromisoformat(rate[3]),
                        is_updated=True if rate[4] == 1 else False,
                    )
                )

            cursor.close()
            return rate_list

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                f"Error while getting exchange_rates closest to: exc_date:{exc_date}, "
            ) from e

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

        if begin_date is None:
            begin_date = date(1, 1, 1)

        if end_date is None:
            end_date = date(9999, 12, 31)

        begin_date = begin_date.isoformat()
        end_date = end_date.isoformat()
        cursor = self._connection.cursor()

        sql = """
            SELECT 
                from_currency,
                to_currency,
                rate,
                rate_date
            FROM 
                exchange_rates 
            WHERE 
                is_updated = 0
                AND rate_date BETWEEN ? AND ? 
        """

        parameters = (begin_date, end_date)

        try:
            cursor.execute(sql, parameters)
            rate_get = cursor.fetchall()

            rate_list = []
            for rate in rate_get:
                rate_list.append(
                    ExchangeRate(
                        from_currency=rate[0],
                        to_currency=rate[1],
                        rate=rate[2],
                        rate_date=date.fromisoformat(rate[3]),
                        is_updated=False,
                    )
                )

            cursor.close()
            return rate_list

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                "Error while getting not updated exchange_rates. ",
            ) from e

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

        cursor = self._connection.cursor()

        # Since we have the possibility to handle multiple user at the same time
        # also with mutli-threading, there is the possibility that this funciton is
        # called multiple times in the same istance. Since sqlite lock the
        # table with the given name, that table must be unique.
        # - are interpreted as minus
        temp_table_name = "tmp_" + str(uuid.uuid4()).replace("-", "_")

        try:
            cursor.execute("PRAGMA temp_store = MEMORY")

            cursor.execute(
                f"""
                CREATE TEMP TABLE {temp_table_name} (
                    check_date TEXT PRIMARY KEY
                )
            """
            )

            if not isinstance(date_list, list):
                date_list = [date_list]

            # Use only unique dates
            date_list = list(set(date_list))

            date_tuple = [(d.isoformat(),) for d in date_list]

            sql = f"""
                INSERT INTO {temp_table_name} 
                    (check_date)
                VALUES
                    (?)
            """
            cursor.executemany(sql, date_tuple)

            sql = f"""
                SELECT
                    t_d.check_date
                FROM
                     {temp_table_name} t_d
                LEFT JOIN
                    exchange_rates e ON t_d.check_date = e.rate_date
                WHERE
                    e.rate_date IS NULL
            """

            cursor.execute(sql)
            date_get = cursor.fetchall()
            return [date.fromisoformat(dt[0]) for dt in date_get]

        except sqlite3.DatabaseError as e:
            raise RepositoryError("Error while getting missing rates dates.") from e

        finally:
            cursor.execute(f"DROP TABLE IF EXISTS {temp_table_name} ")
            cursor.close()

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

        cursor = self._connection.cursor()

        sql = """
            UPDATE exchange_rates SET
                rate = ?,
                is_updated = ?
            WHERE
                from_currency = ? AND
                to_currency = ? AND
                rate_date = ?
        """

        parameters = (
            new_exch.rate,
            1 if new_exch.is_updated else 0,
            new_exch.from_currency,
            new_exch.to_currency,
            new_exch.rate_date.isoformat(),
        )

        self._validate_edit_delete(new_exch)

        try:
            cursor.execute(sql, parameters)
            cursor.close()

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                "Error while editing exchange_rate with: ", f"new_exc:{new_exch}. "
            ) from e

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

        cursor = self._connection.cursor()

        sql = """
            DELETE FROM 
                exchange_rates 
            WHERE
                from_currency = ? AND
                to_currency = ? AND
                rate_date = ?;
        """

        parameters = (
            exc.from_currency,
            exc.to_currency,
            exc.rate_date.isoformat(),
        )

        self._validate_edit_delete(exc)

        try:
            cursor.execute(sql, parameters)
            cursor.close()

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                "Error while deleting exchange_rate with: ", f"exc:{exc}. "
            ) from e

    def _validate_edit_delete(self, exc: ExchangeRate) -> None:
        """Check if the given exchange rate exist in the db.

        If nothing is found an EntityNotFoundError is raised.
        """

        cursor = self._connection.cursor()

        sql = """
            SELECT 1
            FROM
                exchange_rates
            WHERE
                from_currency = ? AND
                to_currency = ? AND
                rate_date = ?
        """

        parameters = (
            exc.from_currency,
            exc.to_currency,
            exc.rate_date.isoformat(),
        )

        exc_get = cursor.execute(sql, parameters).fetchone()
        cursor.close()
        if exc_get is None:
            raise EntityNotFoundError("transaction", f"exc:{exc}")
