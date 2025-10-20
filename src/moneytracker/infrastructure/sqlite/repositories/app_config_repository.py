import sqlite3
from datetime import date

from moneytracker.core.domain.exchange_rate import Currency
from moneytracker.core.exceptions import DuplicateEntityError, EntityNotFoundError, RepositoryError
from moneytracker.core.repositories.abstract_app_config_repository import (
    AbstractAppConfigRepository,
)


class AppConfigRepostiory(AbstractAppConfigRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, name: str, value: str) -> None:
        cursor = self._connection.cursor()

        sql = """
            INSERT INTO app_config (
                name,
                value
            )
            VALUES
                (?, ?)
        """

        parameters = (name, value)

        try:
            cursor.execute(sql, parameters)

            cursor.close()

        except sqlite3.DatabaseError as e:
            if "UNIQUE constraint failed" in str(e):
                raise DuplicateEntityError(
                    f"Unique constraint error on app config's name: name:{name}"
                ) from e
            raise RepositoryError(
                f"Error while adding app configuration's parameter. name:{name}, value:{value}"
            ) from e

    def get(self, name: str) -> str | None:
        cursor = self._connection.cursor()

        sql = """
            SELECT
                value
            FROM 
                app_config
            WHERE 
                name = ?
        """

        parameters = (name,)

        try:
            cursor.execute(sql, parameters)
            value = cursor.fetchone()

            cursor.close()

            if value is not None:
                return value[0]
            else:
                return None

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                f"Error while getting app configuration's parameter. name:{name}"
            ) from e

    def edit(self, name: str, new_value: str) -> None:
        cursor = self._connection.cursor()

        sql = """
            UPDATE
                app_config
            SET
                value = ?
            WHERE
                name = ?
        """

        parameters = (new_value, name)

        self._validate_edit_delete(name)

        try:
            cursor.execute(sql, parameters)
            cursor.close()

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                f"Error while editing app configuration's parameter. "
                f"name:{name}, new_value:{new_value}"
            ) from e

    def delete(self, name: str) -> None:
        cursor = self._connection.cursor()

        sql = """
            DELETE FROM 
                app_config
            WHERE
                name = ?
        """
        parameters = (name,)

        self._validate_edit_delete(name)

        try:
            cursor.execute(sql, parameters)
            cursor.close()

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                f"Error while delting app configuration's parameter. name:{name}"
            ) from e

    def _validate_edit_delete(self, name: str) -> None:
        """Check if the given config name exist in the db.

        If nothing is found an EntityNotFoundError is raised.
        """

        cursor = self._connection.cursor()

        sql = """
            SELECT 1
            FROM
                app_config
            WHERE
                name = ?
        """

        parameters = (name,)

        exc_get = cursor.execute(sql, parameters).fetchone()
        cursor.close()
        if exc_get is None:
            raise EntityNotFoundError("app_config", f"name:{name}")

    def add_upd_currency_list(self, currency_list: list[Currency]) -> None:
        cursor = self._connection.cursor()

        sql = """
            INSERT INTO currencies (
                code,
                symbol,
                name,
                is_active,
                deprecation_date
            )
            VALUES
                (?, ?, ?, ?, ?)
            ON CONFLICT
                (code)
            DO UPDATE SET
                is_active = excluded.is_active,
                deprecation_date = excluded.deprecation_date;
        """

        parameters = []
        for curr in currency_list:
            if curr.deprecation_date is not None:
                depr_date = curr.deprecation_date.isoformat()
            else:
                depr_date = None

            parameters.append(
                (
                    curr.code,
                    curr.symbol,
                    curr.name,
                    1 if curr.is_active else 0,
                    depr_date,
                )
            )

        try:
            cursor.executemany(sql, parameters)
            cursor.close()

        except sqlite3.DatabaseError as e:
            raise RepositoryError("Error while adding or updating currencies: ") from e

    def get_currency_list(self, is_active: bool | None = None) -> list[Currency]:
        cursor = self._connection.cursor()

        sql = """
            SELECT
                code,
                symbol,
                name,
                is_active,
                deprecation_date
            FROM 
                currencies
        """

        parameters = []
        if is_active is not None:
            sql += " WHERE is_active = ?"
            parameters = (1 if is_active else 0,)

        try:
            cursor.execute(sql, parameters)
            currencies = cursor.fetchall()

            currency_list = []
            for curr in currencies:
                if curr[4] is not None:
                    dep_date = date.fromisoformat(curr[4])
                else:
                    dep_date = None

                currency_list.append(
                    Currency(
                        code=curr[0],
                        symbol=curr[1],
                        name=curr[2],
                        is_active=True if curr[3] == 1 else False,
                        deprecation_date=dep_date,
                    )
                )

            cursor.close()

            return currency_list

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                f"Error while getting app currencies. is_active:{is_active}",
            ) from e
