import sqlite3
from datetime import date

from src.core.domain.exchange_rate import ExchangeRate
from src.core.exceptions import DuplicateEntityError, EntityNotFoundError, RepositoryError
from src.core.repositories.abstract_exchange_rate_repository import AbstractExchangeRateRepository


class ExchangeRateRepository(AbstractExchangeRateRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, exc_list: list[ExchangeRate] | ExchangeRate) -> None:
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

        except sqlite3.DatabaseError as e:
            if "UNIQUE constraint failed" in str(e):
                raise DuplicateEntityError("Unique constrainnt error") from e

            raise RepositoryError("Error while adding exchange rates.") from e

    def get(
        self,
        exc_date: date,
        from_currency: str | None = None,
        to_currency: str | None = None,
    ) -> list[ExchangeRate]:
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

            return rate_out

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                "Error while getting exchange_rates: "
                f"exc_date:{exc_date}, "
                f"from_currency:{from_currency}, "
                f"to_currency:{to_currency}. "
            ) from e

    def get_closest(self, exc_date: date) -> list[ExchangeRate]:
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

            return rate_list

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                "Error while getting not updated exchange_rates. ",
            ) from e

    def get_missing_rates_dates(self, date_list: list[date] | date) -> list[date]:
        cursor = self._connection.cursor()

        try:
            cursor.execute("PRAGMA temp_store = MEMORY")

            cursor.execute(
                """
                CREATE TEMP TABLE temp_dates_to_check (
                    check_date TEXT PRIMARY KEY
                )
            """
            )

            if not isinstance(date_list, list):
                date_list = [date_list]

            # Use only unique dates
            date_list = list(set(date_list))

            date_tuple = [(d.isoformat(),) for d in date_list]

            sql = """
                INSERT INTO temp_dates_to_check 
                    (check_date)
                VALUES
                    (?)
            """
            cursor.executemany(sql, date_tuple)

            sql = """
                SELECT
                    t_d.check_date
                FROM
                    temp_dates_to_check t_d
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
            cursor.execute("DROP TABLE IF EXISTS temp_dates_to_check")

    def edit(self, new_exch: ExchangeRate) -> None:
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

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                "Error while editing exchange_rate with: ", f"new_exc:{new_exch}. "
            ) from e

    def delete(self, exc: ExchangeRate) -> None:
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
        if exc_get is None:
            raise EntityNotFoundError("transaction", f"exc:{exc}")
