import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError

from src.api import security
from src.core.exceptions import UnauthorizedException

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_id_user(token: str = Depends(oauth2_scheme)) -> int:
    try:
        payload = jwt.decode(token, security.SECRET_KEY, security.ALGORITHM)

        id_user = payload.get("sub")

        # jwt encode it as a string
        id_user = int(id_user)

        # TODO: Here add a check if the id_user exist in the database such that the
        # token is not used if the user is deleted

        return id_user

    except InvalidTokenError as e:
        print(str(e))
        raise UnauthorizedException()
