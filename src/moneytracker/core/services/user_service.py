import logging

from argon2 import PasswordHasher

from moneytracker.core.domain.user import UserOut
from moneytracker.core.exceptions import (
    OperationNotPermittedError,
    RepositoryError,
    ServiceError,
    ServiceUserNotFoundError,
    UsernameAlreadyPresentError,
)
from moneytracker.infrastructure.job_manager import (
    complete_task,
)
from moneytracker.infrastructure.sqlite.unit_of_work import UnitOfWork
from moneytracker.infrastructure.worker import (
    ADD_USER_TASK_NAME,
    DELETE_USER_TASK_NAME,
    EDIT_USER_TASK_NAME,
)

logger = logging.getLogger(__name__)


class UserService:
    def add(self, uow: UnitOfWork, username: str, password: str) -> int:
        """Add a users to the database.

        Parameters
        ----------
            - username (str) : username of the new User
            - password (str) : password of the new User

        Returns
        -------
            The id_user is returned

        Raises
        ------
            - UsernameAlreadyPresentError: If the provided user's username is already
                present in the database.
            - ServiceError: If something went wrong with the repository or the service.

        Notes
        -----
            Before saving the password in the database, it is hashed with the
            Argon2 algorithm.
            The default user settings are also added for that new user.
        """

        logger.info("Saving new user")

        try:
            try:
                ph = PasswordHasher()
                hashed_password = ph.hash(password)
            except Exception as e:
                logger.exception(str(e))
                raise ServiceError(
                    "An unexpected error occurred while hashing the password."
                ) from e

            with uow:
                user_list = uow.user.get(None)

            usernames = [user.username for user in user_list]

            if username in usernames:
                logger.info(f"The username:{username} is already present in the database")
                raise UsernameAlreadyPresentError("Username already in use")

            args = (username, hashed_password)
            result = complete_task(ADD_USER_TASK_NAME, args)

            id_user = result["id_user"]

            return id_user

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def authenticate(
        self,
        uow: UnitOfWork,
        username: str,
        password: str,
    ) -> UserOut | None:
        """Authenticate a user.

        Parameters
        ----------
            - username (str) : username of the user
            - password (str) : non hashed password

        Returns
        -------
            A User instance if the user is authenticated. If not, None is returned.

        Raises
        ------
            - ServiceError: If something went wrong with the repository or the service.
        """

        logger.info("Authenticating user")
        try:
            with uow:
                user_list = uow.user.get(username)

                if not user_list:
                    return None

                user = user_list[0]
                stored_hash = user.password

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

        try:
            ph = PasswordHasher()
            ph.verify(stored_hash, password)

            return user

        except Exception:
            return None

    def get(self, uow: UnitOfWork, username: str | None) -> list[UserOut]:
        """Get User with the given username.

        Parameters
        ----------
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

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def edit(
        self,
        uow: UnitOfWork,
        id_user: int,
        new_username: str | None,
        new_password: str | None,
        old_password: str | None,
    ) -> None:
        """Edit a User present in the database.

        The only parameter that can be changed are:
        - username;
        - password.

        id can't be changed.
        To change the password, the old password is required.
        To change the username, the old password is not required.


        Parameters
        ----------
            - id_user (int) : id of the user to be modified,
            - new_username (str or None) : new username. If None, the username is
                not modified,
            - new_password (str or None) : new password of the user. If None, the
                password is not modified,
            - old_password (str) : current_password of the user. Can be None only if
                editing the username. If the password is to be modified, this
                parameter is required.

        Raises
        ------
            - OperationNotPermittedError: If the given old_password is not correct or
                is not given (ie is None when trying to change the password).
            - UsernameAlreadyPresentError: If the new username is already in use.
            - ServiceUserNotFoundError: If the user with the given id_user is not in the db.
            - ServiceError: If something went wrong with the repository or the service.
        """

        logger.info("Editing user")

        try:
            with uow:
                user = uow.user.get_by_id(id_user)

            if user is None:
                logger.error(f"User with id:{id_user} not found")
                raise ServiceUserNotFoundError(
                    "The user with the given id is not present in the database",
                )

            if new_password is not None:
                if old_password is None:
                    logger.error(
                        "Changing password without providing the old one is prohibited",
                    )
                    raise OperationNotPermittedError(
                        "Changing password without providing the old one is prohibited",
                    )

                try:
                    ph = PasswordHasher()
                    ph.verify(user.password, old_password)
                    password = ph.hash(new_password)

                except Exception:
                    logger.error(
                        "The current password doesn't match the provided old_password",
                    )
                    raise OperationNotPermittedError(
                        "The current password doesn't match the provided old_password",
                    )
            else:
                password = user.password

            if new_username is not None:
                with uow:
                    user_list = uow.user.get(None)

                username_list = [user.username for user in user_list]

                if new_username in username_list:
                    logger.error(f"Username: {new_username} already present in the database")
                    raise UsernameAlreadyPresentError("Username already in use")

                username = new_username

            else:
                username = user.username

            args = (id_user, username, password)
            complete_task(EDIT_USER_TASK_NAME, args)

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def delete(self, uow: UnitOfWork, id_user: int, current_password: str) -> None:
        """Delete a User from the database if the given password is correct.

        Parameters
        ----------
            - id_user (int) : id of the User to be deleted.
            - current_password (str) : current password of the user.

        Raises
        ------
            - OperationNotPermitterError: If the provided password doesn't match the
                one in the database.
            - ServiceUserNotFoundError: If the user with the given id_user is not in the db.
            - ServiceError: If something went wrong with the repository or the service.
        """

        logger.info(f"Deleting user with id_user: {id_user}")

        try:
            with uow:
                user = uow.user.get_by_id(id_user)

            if user is None:
                logger.error(f"User with id:{id_user} not found")
                raise ServiceUserNotFoundError(
                    "The user with the given id is not present in the database",
                )

            try:
                ph = PasswordHasher()
                ph.verify(user.password, current_password)

            except Exception:
                logger.error(
                    "The current password doesn't match the provided old_password",
                )
                raise OperationNotPermittedError(
                    "The current password doesn't match the provided old_password",
                )

            args = (id_user,)
            complete_task(DELETE_USER_TASK_NAME, args)

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e
