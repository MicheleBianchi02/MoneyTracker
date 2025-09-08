from datetime import datetime, timedelta, timezone

import jwt
from pydantic import BaseModel

# TODO: put the key elsewhere
# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1000


class Token(BaseModel):
    access_token: str
    token_type: str


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> Token:
    # only the first layer get copied. If the value is a list, it still point to
    # the original list.
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta

        to_encode.update({"exp": expire})

    # If the expiires_delta is None, the expiration date is not checked

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
