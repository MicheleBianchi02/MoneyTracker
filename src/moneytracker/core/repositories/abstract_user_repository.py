from abc import ABC, abstractmethod

from moneytracker.core.domain.user import UserOut


class AbstractUserRepository(ABC):
    @abstractmethod
    def add(self, username: str, password: str) -> int:
        """Add a users to the database.

        Parameters
        ----------
            - username (str) : username of the new User
            - password (str) : password of the new User

        Returns
        -------
            id of the new User.

        Raises
        ------
            - DuplicateEntityError: If Unique constraint error occour (e.g. two identical
                user are inserted)
            - RepositoryError: If something went wrong with the database

        Notes
        -----
            Users are considered unique in the db if they have different username.
        """

        raise NotImplementedError

    @abstractmethod
    def get(self, username: str | None) -> list[UserOut]:
        """Get User with the given username.

        Paramters
        ---------
            - username (str or None) : username of the required user. If None all the
            Users in the db are returned

        Returns
        -------
            A list containing all the required Users. Even if the usename is not None,
            a list with a unique User is still returned.

        Raises
        ------
            RepositoryError: If something went wrong with the database
        """

        raise NotImplementedError

    @abstractmethod
    def edit(self, new_user: UserOut) -> None:
        """Edit a User present in the database.

        The only parameter that can be changed are:
        - username;
        - password.

        id can't be changed.
        If the user with the given id is not present in the database,
        nothing is done.

        Parameters
        ----------
            - new_user (User) : User with the new updated values.
                Important: The id of the input User should be the same of the old
                one.

        Raises
        ------
            - DuplicateEntityError: If Unique constraint error occour (e.g. two user
                user with the same username are inserted)
            - ForeignKeyError: If the user with the given id_user is not in the db.
            - RepositoryError: If something went wrong with the database
        """

        raise NotImplementedError

    @abstractmethod
    def delete(self, id_user: int) -> None:
        """Delete a User from the database.

        If the user with the given id is not present in the database,
        nothing is done.

        Parameters
        ----------
            id_user (int) : id of the User to be deleted.

        Raises
        ------
            RepositoryError: If something went wrong with the database
        """

        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, id_user: int) -> UserOut | None:
        """Return an instance of UserOut of the user with the given id

        Parameters
        ----------
            id_user (int) : id of the User.

        Returns
        -------
            An instance of UserOut if the user is found in the database. If no
            user is present in the database with the given id_user, None is returned.

        Raises
        ------
            RepositoryError: If something went wrong with the database
        """
