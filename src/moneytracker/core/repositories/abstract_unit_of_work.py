from abc import ABC, abstractmethod, abstractproperty

from moneytracker.core.repositories.abstract_app_config_repository import (
    AbstractAppConfigRepository,
)
from moneytracker.core.repositories.abstract_category_repository import AbstractCategoryRepository
from moneytracker.core.repositories.abstract_exchange_rate_repository import (
    AbstractExchangeRateRepository,
)
from moneytracker.core.repositories.abstract_transaction_repository import (
    AbstractTransactionRepository,
)
from moneytracker.core.repositories.abstract_user_repository import AbstractUserRepository
from moneytracker.core.repositories.abstract_user_setting_repository import (
    AbstractUserSettingRepository,
)


class AbstractUnitOfWork(ABC):
    """Handle atomic db operation.

    Guarantee that all the transactions happen correctly before saving them (commit).
    If some exeption occour, a roolback is done. Those transaction are lost but the
    integrity of the system is mantained.
    If some error occoured, in order for this to work correctly any type of exeption
    must be raised.
    """

    def __enter__(self) -> "AbstractUnitOfWork":
        """Called when entering the 'with' block."""

        raise NotImplementedError

    def __exit__(self, exc_type, exc_val, traceback):
        """
        Called when exiting the 'with' block.
        exc_type, exc_val, traceback will be None if no exception occurred.
        Otherwise, they contain the exception info.
        """

        # If an exeption is raised __exit__ will still raise the expeption. If you
        # don't want to use any try block, you need to return in the concrete
        # class something in the __exit__ block.

        # If the .__exit__() method returns True, then any exception that occurs in the
        # with block is swallowed and the execution continues at the next statement after
        # with. If .__exit__() returns False, then exceptions are propagated out of the
        # context (i.e. exiting the program if not captured). This is also the default
        # behavior when the method doesn’t return anything explicitly.

        raise NotImplementedError

    @abstractmethod
    def commit(self) -> None:
        """Commit all the changes"""
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        """Rollback all the changes.
        Used when an exeption occoured"""
        raise NotImplementedError

    @abstractproperty
    def user(self) -> AbstractUserRepository:
        raise NotImplementedError

    @abstractproperty
    def category(self) -> AbstractCategoryRepository:
        raise NotImplementedError

    @abstractproperty
    def transaction(self) -> AbstractTransactionRepository:
        raise NotImplementedError

    @abstractproperty
    def user_setting(self) -> AbstractUserSettingRepository:
        raise NotImplementedError

    @abstractproperty
    def app_config(self) -> AbstractAppConfigRepository:
        raise NotImplementedError

    @abstractproperty
    def exchange_rate(self) -> AbstractExchangeRateRepository:
        raise NotImplementedError
