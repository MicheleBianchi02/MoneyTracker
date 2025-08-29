import sqlite3

from src.core.exceptions import DuplicateEntityError, RepositoryError
from src.core.repositories.abstract_app_config_repository import AbstractAppConfigRepository


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

        try:
            cursor.execute(sql, parameters)
            cursor.close()

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                f"Error while delting app configuration's parameter. name:{name}"
            ) from e
