import logging
import uuid

from argon2 import PasswordHasher

from src.core.domain.user import User
from src.core.exceptions import (
    RepositoryError,
    ServiceError,
    ServiceUserNotFoundError,
    UsernameAlreadyPresentError,
)
from src.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from src.infrastructure.job_manager import job_manager
from src.infrastructure.task_queue import task_queue
from src.infrastructure.worker import ADD_USER_TASK_NAME

logger = logging.getLogger(__name__)


class UserService:
    def add(self, uow: AbstractUnitOfWork, username: str, password: str) -> str:
        """Add a users to the database.

        Parameters
        ----------
            - username (str) : username of the new User
            - password (str) : password of the new User

        Returns
        -------
            The corresponding job_id. At the beginning the job_status will be pending.
            When the worker thread finished the operation, the job status get updated.

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

        job_id = str(uuid.uuid4())

        try:
            ph = PasswordHasher()
            hashed_password = ph.hash(password)

            with uow:
                user_list = uow.user.get(None)

            usernames = [user.username for user in user_list]

            if username in usernames:
                logger.info(f"The username:{username} is already present in the database")
                raise UsernameAlreadyPresentError("Username already in use")

            job_manager.add_job(job_id)

            args = (username, hashed_password)
            task_queue.put((ADD_USER_TASK_NAME, job_id, args), block=True)

            return job_id

        except (RepositoryError, Exception) as e:
            # This incude also error from the argon2 library
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def authenticate(self, uow: AbstractUnitOfWork, username: str, password: str) -> bool:
        """Authenticate a user.

        Parameters
        ----------
            - username (str) : username of the user
            - password (str) : non hashed password

        Returns
        -------
            A bool value whether the user has been authenticated or not

        Raises
        ------
            - ServiceError: If something went wrong with the repository or the service.
        """

        logger.info("Authenticating user")
        try:
            with uow:
                user_list = uow.user.get(username)

                if not user_list:
                    return False

                stored_hash = user_list[0].password

        except (RepositoryError, Exception) as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

        try:
            ph = PasswordHasher()
            ph.verify(stored_hash, password)

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

    def edit(self, uow: AbstractUnitOfWork, new_user: User) -> str:
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

        Returns
        -------
            The corresponding job_id. At the beginning the job_status will be pending.
            When the worker thread finished the operation, the job status get updated.

        Raises
        ------
            - UsernameAlreadyPresentError: If the new username is already in use.
            - ServiceUserNotFoundError: If the user with the given id_user is not in the db.
            - ServiceError: If something went wrong with the repository or the service.
        """

        logger.info("Editing user")
        job_id = str(uuid.uuid4())

        try:
            ph = PasswordHasher()
            hashed_password = ph.hash(new_user.password)

            new_user.password = hashed_password

            with uow:
                user_list = uow.user.get(None)

            id_exist = False
            username_valid = False
            for user in user_list:
                if new_user.id == user.id:
                    id_exist = True

                if new_user.username == user.username:
                    username_valid = True

            if not id_exist:
                logger.error(f"User with id: {new_user.id} not found")
                raise ServiceUserNotFoundError(
                    "The user with the given id is not present in the database",
                )

            if not username_valid:
                logger.error(f"Username: {new_user.username} already present in the database")
                raise UsernameAlreadyPresentError("Username already in use")

            job_manager.add_job(job_id)

            args = (new_user,)
            task_queue.put((ADD_USER_TASK_NAME, job_id, args), block=True)

            return job_id

        except (RepositoryError, Exception) as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def delete(self, uow: AbstractUnitOfWork, id_user: int) -> str:
        """Delete a User from the database.

        Parameters
        ----------
            id_user (int) : id of the User to be deleted.

        Returns
        -------
            The corresponding job_id. At the beginning the job_status will be pending.
            When the worker thread finished the operation, the job status get updated.

        Raises
        ------
            - ServiceUserNotFoundError: If the user with the given id_user is not in the db.
            - ServiceError: If something went wrong with the repository or the service.
        """

        logger.info(f"Deleting user with id_user: {id_user}")

        job_id = str(uuid.uuid4())
        try:
            with uow:
                user_list = uow.user.get(None)

            id_list = [user.id for user in user_list]

            if id_user not in id_list:
                logger.error(f"User with id: {id_user} not found")
                raise ServiceUserNotFoundError(
                    "The user with the given id is not present in the database",
                )

            job_manager.add_job(job_id)

            args = (id_user,)
            task_queue.put((ADD_USER_TASK_NAME, job_id, args), block=True)

            return job_id

        except (RepositoryError, Exception) as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e
