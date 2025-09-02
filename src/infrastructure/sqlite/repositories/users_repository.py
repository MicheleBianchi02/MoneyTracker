import sqlite3

from src.core.domain.user import User
from src.core.exceptions import DuplicateEntityError, EntityNotFoundError, RepositoryError
from src.core.repositories.abstract_user_repository import AbstractUserRepository

# NOTE: This part save the password as plain text, meaning that it is needed
# a script for hashing the password in a more abstract layer of the app.


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
                raise DuplicateEntityError(
                    f"Unique constrainnt error on username:{username}"
                ) from e

            raise RepositoryError("Error while adding users to the database.") from e

    def get(self, username: str | None) -> list[User]:
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
                user = User(
                    id=user_ret[0],
                    username=user_ret[1],
                    password=user_ret[2],
                )

                user_list.append(user)

            cursor.close()
            return user_list

        except sqlite3.DatabaseError as e:
            raise RepositoryError(f"Error while getting user with: username:{username}. ") from e

    def edit(self, new_user: User) -> None:
        cursor = self._connection.cursor()

        sql = """
        UPDATE 
            users 
        SET 
            username = ?, password = ? 
        WHERE
            id_user = ?
        """

        parameters = (new_user.username, new_user.password, new_user.id)

        self.validate_id_user(new_user.id)

        try:
            cursor.execute(sql, parameters)
            cursor.close()

        except sqlite3.DatabaseError as e:
            if "UNIQUE constraint failed" in str(e):
                raise DuplicateEntityError(
                    f"Unique constrainnt error on username:{new_user.username}"
                ) from e

            raise RepositoryError(
                f"Error while editing User: new_user:{new_user}. ",
            ) from e

    def delete(self, id_user: int) -> None:
        cursor = self._connection.cursor()

        sql = """
            DELETE FROM 
                users 
            WHERE id_user = ?
        """

        parameter = (id_user,)

        self.validate_id_user(id_user)

        try:
            cursor.execute(sql, parameter)
            cursor.close()

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                f"Error while deleting User from database with: id_user:{id_user}",
            ) from e

    def validate_id_user(self, id_user: int) -> None:
        cursor = self._connection.cursor()

        sql = """
            SELECT 1
            FROM
                users
            WHERE
                id_user = ?;
        """

        parameters = (id_user,)

        user_get = cursor.execute(sql, parameters).fetchone()
        cursor.close()
        if user_get is None:
            raise EntityNotFoundError("user", f"id_user:{id_user}")
