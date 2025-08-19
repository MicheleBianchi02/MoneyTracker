import logging

from argon2 import PasswordHasher

from src.core.domain.user import User
from src.core.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    RepositoryError,
    ServiceError,
    UsernameAlreadyPresentError,
    UserNotFoundError,
)
from src.core.repositories.abstract_unit_of_work import AbstractUnitOfWork

logger = logging.getLogger(__name__)


class UserService:
    def add(self, uow: AbstractUnitOfWork, username: str, password: str) -> int:
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
            - UsernameAlreadyPresentError: If the provided user's username is already
                present in the database.
            - ServiceError: If something went wrong with the repository or the service.

        Notes
        -----
            Before saving the password in the database, it is hashed with the
            Argon2 algorithm.
        """

        logger.info("Saving new user")

        try:
            ph = PasswordHasher()
            hashed_password = ph.hash(password)

            with uow:
                return uow.user.add(username, hashed_password)

        except DuplicateEntityError as e:
            logger.info(f"The username:{username} is already present in the database")
            raise UsernameAlreadyPresentError("Username already in use") from e

        except (RepositoryError, Exception) as e:
            # This incude also error from the argon2 library
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def authenticate(self, uow: AbstractUnitOfWork, username: str, password: str) -> bool:
        logger.info("Authenticating user")
        try:
            with uow:
                stored_hash = uow.user.get(username)[0]

        except (RepositoryError, Exception) as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

        try:
            ph = PasswordHasher()
            ph.verify(stored_hash.password, password)

            return True

        except Exception:
            return False

    def get(self, uow: AbstractUnitOfWork, username: str | None) -> list[User]:
        """Get User with the given username.

        Paramters

            - username (str or None) : username of the required user. If None all the
            Users in the db are returned

        Returns
        -------
            A list containing all the required Users. Even if the usename is not None,
            a list with a unique User is still returned.

        Raises
        ------
            - ServiceError: If something went wrong with the repository or the service.
        """

        logger.info("Getting user")

        try:
            with uow:
                return uow.user.get(username)

        except (RepositoryError, Exception) as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def edit(self, uow: AbstractUnitOfWork, new_user: User) -> None:
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
            - UsernameAlreadyPresentError: If the new username is already in use.
            - UserNotFoundError: If the user with the given id_user is not in the db.
            - ServiceError: If something went wrong with the repository or the service.
        """

        logger.info("Editing user")

        try:
            ph = PasswordHasher()
            hashed_password = ph.hash(new_user.password)

            new_user.password = hashed_password

            with uow:
                uow.user.edit(new_user)

        except DuplicateEntityError as e:
            logger.info(
                f"The username:{new_user.username} is already present in the database",
            )
            raise UsernameAlreadyPresentError("Username already in use") from e

        except EntityNotFoundError as e:
            logger.error(f"{str(e)}")
            raise UserNotFoundError(
                "The user with the given id is not present in the database",
            ) from e

        except (RepositoryError, Exception) as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def delete(self, uow: AbstractUnitOfWork, id_user: int) -> None:
        """Delete a User from the database.

        Parameters
        ----------
            id_user (int) : id of the User to be deleted.

        Raises
        ------
            - UserNotFoundError: If the user with the given id_user is not in the db.
            - ServiceError: If something went wrong with the repository or the service.
        """

        logger.info(f"Deleting user with id_user: {id_user}")

        try:
            with uow:
                uow.user.delete(id_user)

        except EntityNotFoundError as e:
            logger.error(f"{str(e)}")
            raise UserNotFoundError(
                "The user with the given id is not present in the database",
            ) from e

        except (RepositoryError, Exception) as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e
