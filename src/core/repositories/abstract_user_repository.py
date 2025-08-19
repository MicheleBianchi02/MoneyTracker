from abc import ABC, abstractmethod

from src.core.domain.user import User


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
    def get(self, username: str | None) -> list[User]:
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
    def edit(self, new_user: User) -> None:
        """Edit a User present in the database.

        The only parameter that can be changed are:
        - username;
        - password.

        id can't be changed.

        Parameters
        ----------
            - new_user (User) : User with the new updated values.
                Important: The id of the input User should be the same of the old
                one.

        Raises
        ------
            - DuplicateEntityError: If Unique constraint error occour (e.g. two user
                user with the same username are inserted)
            - EntityNotFounError: If the user with the given id_user is not in the db.
            - RuntimeError: If something went wrong with the database
        """

        raise NotImplementedError

    @abstractmethod
    def delete(self, id_user: int) -> None:
        """Delete a User from the database.

        Parameters
        ----------
            id_user (int) : id of the User to be deleted.

        Raises
        ------
            - EntityNotFounError: If the user with the given id_user is not in the db.
            - RuntimeError: If something went wrong with the database
        """

        raise NotImplementedError
