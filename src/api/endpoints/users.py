from fastapi import APIRouter, Body, Depends

from src.core.domain.user import User
from src.core.exceptions import (
    BadRequestException,
    DuplicateUserException,
    ServiceError,
    ServiceUserNotFoundError,
    UnauthorizedException,
    UsernameAlreadyPresentError,
    UserNotFoundException,
)
from src.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from src.core.services.user_service import UserService
from src.infrastructure.dependencies import get_uow

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
        id_user = user_service.add(uow, username, password)
        return {"message": "User created successfully", "id_user": id_user}

    except UsernameAlreadyPresentError:
        raise DuplicateUserException()
    except ServiceError as e:
        raise BadRequestException(str(e))


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

    except ServiceError as e:
        raise BadRequestException(str(e))


@router.get("/", response_model=list[User])
def get_users(username: str | None = None, uow: AbstractUnitOfWork = Depends(get_uow)):
    """
    Retrieves a list of users.
    """
    try:
        return user_service.get(uow, username)
    except ServiceError as e:
        raise BadRequestException(str(e))


@router.put("/", status_code=204)
def edit_user(new_user: User, uow: AbstractUnitOfWork = Depends(get_uow)):
    """
    Edits an existing user.
    """
    try:
        user_service.edit(uow, new_user)
        return
    except UsernameAlreadyPresentError:
        raise DuplicateUserException()
    except ServiceUserNotFoundError:
        raise UserNotFoundException()
    except ServiceError as e:
        raise BadRequestException(str(e))


@router.delete("/{id_user}", status_code=204)
def delete_user(id_user: int, uow: AbstractUnitOfWork = Depends(get_uow)):
    """
    Deletes a user.
    """
    try:
        user_service.delete(uow, id_user)
        return
    except ServiceUserNotFoundError:
        raise UserNotFoundException()
    except ServiceError as e:
        raise BadRequestException(str(e))
