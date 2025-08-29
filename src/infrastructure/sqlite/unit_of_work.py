import sqlite3

from src.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from src.infrastructure.sqlite.repositories.app_config_repository import AppConfigRepostiory
from src.infrastructure.sqlite.repositories.categories_repository import CategoryRepository
from src.infrastructure.sqlite.repositories.exchange_rate_repository import ExchangeRateRepository
from src.infrastructure.sqlite.repositories.transaction_repository import TransactionRepository
from src.infrastructure.sqlite.repositories.user_settings_repository import UserSettingRepository
from src.infrastructure.sqlite.repositories.users_repository import UserRepository


class UnitOfWork(AbstractUnitOfWork):
    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    def __enter__(self):
        # Manually begin the transaction.
        self._connection.execute("BEGIN")

        self._user_repo = UserRepository(self._connection)
        self._cat_repo = CategoryRepository(self._connection)
        self._transaction_repo = TransactionRepository(self._connection, self._cat_repo)
        self._user_setting_repo = UserSettingRepository(self._connection)
        self._app_config = AppConfigRepostiory(self._connection)
        self._exchange_rate_repo = ExchangeRateRepository(self._connection)

        return self

    def __exit__(self, exc_type, exc_val, traceback):
        if not exc_val:
            self.commit()
        else:
            self.rollback()

        # With false the exception are propagated
        return False

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    @property
    def user(self) -> UserRepository:
        return self._user_repo

    @property
    def category(self) -> CategoryRepository:
        return self._cat_repo

    @property
    def transaction(self) -> TransactionRepository:
        return self._transaction_repo

    @property
    def user_setting(self) -> UserSettingRepository:
        return self._user_setting_repo

    @property
    def app_config(self) -> AppConfigRepostiory:
        return self._app_config

    @property
    def exchange_rate(self) -> ExchangeRateRepository:
        return self._exchange_rate_repo

    @property
    def connection(self) -> sqlite3.Connection:
        """Used only in testing"""
        return self._connection
