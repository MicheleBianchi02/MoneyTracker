import jwt
from core.exceptions import UnauthorizedException
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from infrastructure.dependencies import manage_uow
from jwt.exceptions import InvalidTokenError

from moneytracker.api import security

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_id_user(token: str = Depends(oauth2_scheme)) -> int:
    try:
        payload = jwt.decode(token, security.SECRET_KEY, security.ALGORITHM)

        id_user = payload.get("sub")

        # jwt encode it as a string
        id_user = int(id_user)

        # used to check that the user really exist. Otherwise, if we delete the
        # user, then he will have a token with a non existing id_user.

        # For better performance we can save in a list all the available ids at
        # startup and then edit it and the db when deleting a user. At the moment it
        # is not needed since the time required is well below the ms.
        with manage_uow() as uow:
            with uow:
                user = uow.user.get_by_id(id_user)

        if user is None:
            raise UnauthorizedException()

        return id_user

    except InvalidTokenError:
        raise UnauthorizedException()
