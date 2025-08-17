from src.core.domain.user import User
from src.core.exceptions import DuplicateEntityError, EntityNotFoundError
from src.core.repositories.abstract_user_repository import AbstractUserRepository


class FakeUserRepository(AbstractUserRepository):
    def __init__(self, users: list[User] | None = None):
        self._users = users if users is not None else []
        self._next_id = len(self._users) + 1

    def add(self, username: str, password: str) -> int:
        if any(u.username == username for u in self._users):
            raise DuplicateEntityError(f"User with username '{username}' already exists.")
        
        new_user = User(id=self._next_id, username=username, password=password)
        self._users.append(new_user)
        self._next_id += 1
        return new_user.id

    def get(self, username: str | None) -> list[User]:
        if username is None:
            return self._users
        return [u for u in self._users if u.username == username]

    def edit(self, new_user: User) -> None:
        user = next((u for u in self._users if u.id == new_user.id), None)
        if user is None:
            raise EntityNotFoundError("user", f"id_user:{new_user.id}")
        
        user.username = new_user.username
        user.password = new_user.password

    def delete(self, id_user: int) -> None:
        user = next((u for u in self._users if u.id == id_user), None)
        if user is None:
            raise EntityNotFoundError("user", f"id_user:{id_user}")
        self._users.remove(user)
