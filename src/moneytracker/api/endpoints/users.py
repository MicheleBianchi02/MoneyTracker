from fastapi import APIRouter, Depends

from moneytracker.api.dependencies import get_id_user
from moneytracker.api.security import Token, create_access_token
from moneytracker.core.domain.user import UserDeleteConfirmation, UserEdit, UserIn, UserOut
from moneytracker.core.exceptions import (
    DuplicateUserException,
    InternalServerErrorException,
    OperationNotPermittedError,
    ServiceError,
    ServiceUserNotFoundError,
    UnauthorizedException,
    UsernameAlreadyPresentError,
    UserNotFoundException,
)
from moneytracker.core.services.user_service import UserService
from moneytracker.infrastructure.dependencies import get_uow
from moneytracker.infrastructure.sqlite.unit_of_work import UnitOfWork

router = APIRouter(prefix="/users", tags=["Users"])
user_service = UserService()


@router.post("/", status_code=201, response_model=dict[str, str | int])
def add_user(
    user: UserIn,
    uow: UnitOfWork = Depends(get_uow),
):
    """
    Adds a new user.
    """
    try:
        id_user = user_service.add(uow, user.username, user.password)

        data = {"sub": id_user}
        # TODO: keep this in sync with the login_for_access_token function.
        # Add expiration date
        token = create_access_token(data)
        token = Token(access_token=token, token_type="bearer")

        return {"message": "User created successfully", "id_user": id_user, **token.model_dump()}

    except UsernameAlreadyPresentError:
        raise DuplicateUserException()
    except ServiceError:
        raise InternalServerErrorException()


@router.get("/", response_model=list[UserOut])
def get_users(username: str | None = None, uow: UnitOfWork = Depends(get_uow)):
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
    uow: UnitOfWork = Depends(get_uow),
):
    """
    Edits an existing user.
    """
    try:
        user_service.edit(
            uow,
            id_user,
            user.new_username,
            user.new_password,
            user.old_password,
        )

        return {"message": "User edited successfully"}

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
    uow: UnitOfWork = Depends(get_uow),
):
    """
    Deletes a user.
    """
    try:
        user_service.delete(uow, id_user, user.current_password)

    except OperationNotPermittedError:
        raise UnauthorizedException()
    except ServiceUserNotFoundError:
        raise UserNotFoundException()
    except ServiceError:
        raise InternalServerErrorException()
