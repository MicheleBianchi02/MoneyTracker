import copy

from src.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from src.infrastructure.fake_repo.fake_app_config_repository import FakeAppConfigRepository
from src.infrastructure.fake_repo.fake_category_repository import FakeCategoryRepository
from src.infrastructure.fake_repo.fake_exchange_rate_repository import FakeExchangeRateRepository
from src.infrastructure.fake_repo.fake_transaction_repository import FakeTransactionRepository
from src.infrastructure.fake_repo.fake_user_repository import FakeUserRepository
from src.infrastructure.fake_repo.fake_user_setting_repository import FakeUserSettingRepository


class FakeUnitOfWork(AbstractUnitOfWork):
    def __init__(self):
        self._user_repo = FakeUserRepository()
        self._cat_repo = FakeCategoryRepository()
        self._transaction_repo = FakeTransactionRepository(self._cat_repo)
        self._exchange_rate_repo = FakeExchangeRateRepository()
        self._user_setting_repo = FakeUserSettingRepository()
        self._app_config_repo = FakeAppConfigRepository()
        self.committed = False

    def __enter__(self):
        self.committed = False
        self._original_state = {
            "users": copy.deepcopy(self._user_repo._users),
            "categories": copy.deepcopy(self._cat_repo._categories),
            "transactions": copy.deepcopy(self._transaction_repo._transactions),
            "exchange_rates": copy.deepcopy(self._exchange_rate_repo._exchange_rates),
            "user_settings": copy.deepcopy(self._user_setting_repo._user_settings),
            "user_currencies": copy.deepcopy(self._user_setting_repo._user_currencies),
            "app_configs": copy.deepcopy(self._app_config_repo._configs),
            "cat_next_id": copy.deepcopy(self._cat_repo._next_id),
            "tr_next_id": copy.deepcopy(self._transaction_repo._next_id),
            "user_next_id": copy.deepcopy(self._user_repo._next_id),
        }
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()

    def commit(self):
        self.committed = True

    def rollback(self):
        self._user_repo._users = self._original_state["users"]
        self._cat_repo._categories = self._original_state["categories"]
        self._transaction_repo._transactions = self._original_state["transactions"]
        self._exchange_rate_repo._exchange_rates = self._original_state["exchange_rates"]
        self._user_setting_repo._user_settings = self._original_state["user_settings"]
        self._user_setting_repo._user_currencies = self._original_state["user_currencies"]
        self._app_config_repo._configs = self._original_state["app_configs"]
        self._cat_repo._next_id = self._original_state["cat_next_id"]
        self._transaction_repo._next_id = self._original_state["tr_next_id"]
        self._user_repo._next_id = self._original_state["user_next_id"]

    @property
    def user(self) -> FakeUserRepository:
        return self._user_repo

    @property
    def category(self) -> FakeCategoryRepository:
        return self._cat_repo

    @property
    def transaction(self) -> FakeTransactionRepository:
        return self._transaction_repo

    @property
    def user_setting(self) -> FakeUserSettingRepository:
        return self._user_setting_repo

    @property
    def app_config(self) -> FakeAppConfigRepository:
        return self._app_config_repo

    @property
    def exchange_rate(self) -> FakeExchangeRateRepository:
        return self._exchange_rate_repo

