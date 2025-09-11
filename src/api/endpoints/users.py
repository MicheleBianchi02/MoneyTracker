from fastapi import APIRouter, Depends

from src.api.dependencies import get_id_user
from src.core.domain.user import UserDeleteConfirmation, UserEdit, UserIn, UserOut
from src.core.exceptions import (
    DuplicateUserException,
    InternalServerErrorException,
    OperationNotPermittedError,
    ServiceError,
    ServiceUserNotFoundError,
    UnauthorizedException,
    UsernameAlreadyPresentError,
    UserNotFoundException,
)
from src.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from src.core.services.user_service import UserService
from src.infrastructure.dependencies import get_uow
from src.infrastructure.job_manager import COMPLETED_CODE, FAILED_CODE, UNKNOWN_CODE, check_status

router = APIRouter(prefix="/users", tags=["Users"])
user_service = UserService()


@router.post("/", status_code=201, response_model=dict[str, str | int])
def add_user(
    user: UserIn,
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Adds a new user.
    """
    try:
        job_id = user_service.add(uow, user.username, user.password)

        status, result = check_status(job_id)

        id_user = result["id_user"]

        if status == COMPLETED_CODE:
            return {"message": "User created successfully", "id_user": id_user}
        elif status == FAILED_CODE or status == UNKNOWN_CODE:
            raise InternalServerErrorException()

    except UsernameAlreadyPresentError:
        raise DuplicateUserException()
    except ServiceError:
        raise InternalServerErrorException()


@router.get("/", response_model=list[UserOut])
def get_users(username: str | None = None, uow: AbstractUnitOfWork = Depends(get_uow)):
    """
    Retrieves a list of users.
    """
    try:
        return user_service.get(uow, username)
    except ServiceError:
        raise InternalServerErrorException()


@router.put("/", status_code=204)
def edit_user(
    user: UserEdit,
    id_user: int = Depends(get_id_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Edits an existing user.
    """
    try:
        job_id = user_service.edit(
            uow,
            id_user,
            user.new_username,
            user.new_password,
            user.old_password,
        )

        status, result = check_status(job_id)

        if status == COMPLETED_CODE:
            return {"message": "User edited successfully"}
        elif status == FAILED_CODE or status == UNKNOWN_CODE:
            raise InternalServerErrorException()

    except OperationNotPermittedError:
        raise UnauthorizedException()
    except UsernameAlreadyPresentError:
        raise DuplicateUserException()
    except ServiceUserNotFoundError:
        raise UserNotFoundException()
    except ServiceError:
        raise InternalServerErrorException()


@router.delete("/", status_code=204)
def delete_user(
    user: UserDeleteConfirmation,
    id_user: int = Depends(get_id_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Deletes a user.
    """
    try:
        job_id = user_service.delete(uow, id_user, user.current_password)

        status, result = check_status(job_id)

        if status == COMPLETED_CODE:
            return {"message": "User deleted successfully"}
        elif status == FAILED_CODE or status == UNKNOWN_CODE:
            raise InternalServerErrorException()

    except OperationNotPermittedError:
        raise UnauthorizedException()
    except ServiceUserNotFoundError:
        raise UserNotFoundException()
    except ServiceError:
        raise InternalServerErrorException()
