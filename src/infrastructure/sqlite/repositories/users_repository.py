import sqlite3

from core.domain.user import UserOut
from core.exceptions import DuplicateEntityError, RepositoryError
from core.repositories.abstract_user_repository import AbstractUserRepository

# NOTE: This part save the password as plain text, meaning that it is needed
# a script for hashing the password in a more abstract layer of the app (service).


class UserRepository(AbstractUserRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, username: str, password: str) -> int:
        cursor = self._connection.cursor()

        sql = """
            INSERT INTO users
                (username,
                password)
            VALUES
                (?, ?)
        """

        parameters = (username, password)

        try:
            cursor.execute(sql, parameters)
            cursor.close()

            id_user = cursor.lastrowid

            return id_user

        except sqlite3.DatabaseError as e:
            if "UNIQUE constraint failed" in str(e):
                raise DuplicateEntityError(f"Unique constraint error on username:{username}") from e

            raise RepositoryError("Error while adding users to the database.") from e

    def get(self, username: str | None) -> list[UserOut]:
        cursor = self._connection.cursor()

        sql = """
            SELECT
                id_user,
                username,
                password
            FROM 
                users
            """

        parameters = []

        if username is not None:
            sql += "WHERE username = ?"
            parameters.append(username)

        parameters = tuple(parameters)

        try:
            cursor.execute(sql, parameters)
            user_ret_list = cursor.fetchall()

            user_list = []
            for user_ret in user_ret_list:
                user = UserOut(
                    id=user_ret[0],
                    username=user_ret[1],
                    password=user_ret[2],
                )

                user_list.append(user)

            cursor.close()
            return user_list

        except sqlite3.DatabaseError as e:
            raise RepositoryError(f"Error while getting user with: username:{username}. ") from e

    def edit(self, id_user: int, username: str, password: str) -> None:
        cursor = self._connection.cursor()

        sql = """
        UPDATE 
            users 
        SET 
            username = ?, password = ? 
        WHERE
            id_user = ?
        """

        parameters = (username, password, id_user)

        try:
            cursor.execute(sql, parameters)
            cursor.close()

        except sqlite3.DatabaseError as e:
            if "UNIQUE constraint failed" in str(e):
                raise DuplicateEntityError(
                    f"Unique constrainnt error on username:{username}"
                ) from e

            raise RepositoryError(
                f"Error while editing User: "
                f"-username:{username} "
                f"-password:{password} "
                f"-id_user:{id_user} "
            ) from e

    def delete(self, id_user: int) -> None:
        cursor = self._connection.cursor()

        sql = """
            DELETE FROM 
                users 
            WHERE id_user = ?
        """

        parameter = (id_user,)

        try:
            cursor.execute(sql, parameter)
            cursor.close()

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                f"Error while deleting User from database with: id_user:{id_user}",
            ) from e

    def get_by_id(self, id_user: int) -> UserOut | None:
        cursor = self._connection.cursor()

        sql = """
            SELECT
                username,
                password
            FROM 
                users
            WHERE
                id_user = ?
        """

        parameters = (id_user,)

        try:
            cursor.execute(sql, parameters)

            user = cursor.fetchone()

            if user is None:
                return None

            else:
                return UserOut(
                    id=id_user,
                    username=user[0],
                    password=user[1],
                )

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                f"Error while getting User by id: id_user:{id_user}. ",
            ) from e
