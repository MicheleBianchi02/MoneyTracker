from datetime import datetime, timedelta, timezone

import jwt
from pydantic import BaseModel

from moneytracker.core.services.app_config import app_config

# Secret is generated on first run and persisted to:
# ~/.config/MoneyTracker/.../server_settings.json
SECRET_KEY = app_config.get_or_create_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1000


class Token(BaseModel):
    access_token: str
    token_type: str


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    # only the first layer get copied. If the value is a list, it still point to
    # the original list.
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta

        to_encode.update({"exp": expire})

    # If the expires_delta is None, the expiration date is not checked

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
