from src.core.exceptions import DuplicateEntityError
from src.core.repositories.abstract_app_config_repository import AbstractAppConfigRepository


class FakeAppConfigRepository(AbstractAppConfigRepository):
    def __init__(self, configs: dict[str, str] | None = None):
        self._configs = configs if configs is not None else {}

    def add(self, name: str, value: str) -> None:
        if name in self._configs:
            raise DuplicateEntityError(f"Config with name '{name}' already exists.")
        self._configs[name] = value

    def get(self, name: str) -> str | None:
        return self._configs.get(name)

    def edit(self, name: str, new_value: str) -> None:
        if name in self._configs:
            self._configs[name] = new_value

    def delete(self, name: str) -> None:
        if name in self._configs:
            del self._configs[name]
