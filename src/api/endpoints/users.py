from fastapi import APIRouter, Body, Depends

from src.core.domain.user import User
from src.core.exceptions import (
    BadRequestException,
    DuplicateUserException,
    InternalServerErrorException,
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


@router.post("/", status_code=201, response_model=dict)
def add_user(
    username: str = Body(...),
    password: str = Body(...),
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Adds a new user.
    """
    try:
        job_id = user_service.add(uow, username, password)

        status, result = check_status(job_id)

        id_user = result["id_user"]

        if status == COMPLETED_CODE:
            return {"message": "User created successfully", "id_user": id_user}
        elif status == FAILED_CODE or status == UNKNOWN_CODE:
            raise InternalServerErrorException()

    except UsernameAlreadyPresentError:
        raise DuplicateUserException()
    except ServiceError:
        raise BadRequestException()
    except Exception:
        raise InternalServerErrorException()


@router.post("/authenticate/", response_model=dict)
def authenticate_user(
    username: str = Body(...),
    password: str = Body(...),
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Authenticates a user.
    """
    try:
        if user_service.authenticate(uow, username, password):
            return {"status": "authenticated"}
        else:
            raise UnauthorizedException("Invalid credentials")

    except ServiceError:
        raise BadRequestException()
    except Exception:
        raise InternalServerErrorException()


@router.get("/", response_model=list[User])
def get_users(username: str | None = None, uow: AbstractUnitOfWork = Depends(get_uow)):
    """
    Retrieves a list of users.
    """
    try:
        return user_service.get(uow, username)
    except ServiceError:
        raise BadRequestException()
    except Exception:
        raise InternalServerErrorException()


@router.put("/", status_code=204)
def edit_user(new_user: User, uow: AbstractUnitOfWork = Depends(get_uow)):
    """
    Edits an existing user.
    """
    try:
        job_id = user_service.edit(uow, new_user)

        status, result = check_status(job_id)

        if status == COMPLETED_CODE:
            return {"message": "User edited successfully"}
        elif status == FAILED_CODE or status == UNKNOWN_CODE:
            raise InternalServerErrorException()

    except UsernameAlreadyPresentError:
        raise DuplicateUserException()
    except ServiceUserNotFoundError:
        raise UserNotFoundException()
    except ServiceError:
        raise BadRequestException()
    except Exception:
        raise InternalServerErrorException()


@router.delete("/{id_user}", status_code=204)
def delete_user(id_user: int, uow: AbstractUnitOfWork = Depends(get_uow)):
    """
    Deletes a user.
    """
    try:
        job_id = user_service.delete(uow, id_user)

        status, result = check_status(job_id)

        if status == COMPLETED_CODE:
            return {"message": "User deleted successfully"}
        elif status == FAILED_CODE or status == UNKNOWN_CODE:
            raise InternalServerErrorException()

    except ServiceUserNotFoundError:
        raise UserNotFoundException()
    except ServiceError:
        raise BadRequestException()
    except Exception:
        raise InternalServerErrorException()
