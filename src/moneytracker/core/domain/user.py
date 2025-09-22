from pydantic import BaseModel


class UserIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    password: str


# These two below are needed because uvicorn log the requests. And, if
# the password is not inside the body of the request, it would get logged.
class UserDeleteConfirmation(BaseModel):
    current_password: str


class UserEdit(BaseModel):
    new_username: str | None = None
    new_password: str | None = None
    old_password: str | None = None
