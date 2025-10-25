import calendar
import random
import threading
from datetime import date, timedelta
from multiprocessing import Queue

import pytest

from moneytracker.core.domain.category import CategoryIn
from moneytracker.core.domain.exchange_rate import Currency, ExchangeRate
from moneytracker.core.domain.transaction import TransactionIn
from moneytracker.core.services.transaction_service import TransactionService
from moneytracker.infrastructure import task_queue, worker
from moneytracker.infrastructure.connection_pool import ConnectionPool
from moneytracker.infrastructure.exchange_rate_provider.exchange_rate import (
    ExchangeRateProvider,
)
from moneytracker.infrastructure.sqlite.repositories.app_setting_repository import (
    AppSettingRepostiory,
)
from moneytracker.infrastructure.sqlite.unit_of_work import UnitOfWork
from moneytracker.infrastructure.worker import EXC_DATE_CONFIG_NAME
from test.util_test import UtilTest


def get_currency_list(self, is_active) -> list[Currency]:
    exc_provider = ExchangeRateProvider()
    active_currencies = exc_provider.available_currencies_detailed
    curr_list = []
    for curr in active_currencies["currencies"]:
        dep_date = curr.get("deprecation_date", None)
        if dep_date is not None:
            dep_date = date.fromisoformat(dep_date)
        curr_list.append(
            Currency(
                code=curr["code"],
                symbol=curr["symbol"],
                name=curr["name"],
                is_active=True if curr["status"] == "active" else False,
                deprecation_date=dep_date,
            )
        )

    return curr_list


@pytest.fixture
def connection_pool(tmp_path) -> ConnectionPool:
    """Create isolated database environment for each test.
    Add tmp_path to the argument to use the tmp directory for the datbase."""

    # tmp_path is a variable internal to pytest. We don't need to define it
    # Create temporary database file
    db_path = tmp_path / "database.db"

    db_path = str(db_path)

    # db_path = ":memory:"  # use in memory database

    connection_pool = ConnectionPool(db_path, max_connections=2)

    return connection_pool


@pytest.fixture
def isolated_worker(monkeypatch, connection_pool):
    """Starts a worker with an isolated task queue for each test."""
    q = Queue()
    monkeypatch.setattr(task_queue, "task_queue", q)

    monkeypatch.setattr(AppSettingRepostiory, "get_currency_list", get_currency_list)

    uow_worker = UnitOfWork(connection_pool._get_connection())
    worker_thread = threading.Thread(target=worker.writer_worker, args=(uow_worker,), daemon=False)
    worker_thread.start()

    yield

    worker.end_worker()
    worker_thread.join(timeout=5)


def test_add_transaction(connection_pool, isolated_worker):
    """In this test we just need to see if the exchange rates are added correctly.
    Because adding the transaction will simply call uow.transactions.add that has
    already been tested in repositories's test"""

    tr_service = TransactionService()
    uow = UnitOfWork(connection_pool._get_connection())

    starting_date = "2025-01-01"
    maximum_date = "2025-05-31"

    tr_date_list = []

    tr_date_list.append(date(2025, 1, 1))
    tr_date_list.append(date(2025, 1, 2))
    tr_date_list.append(date(2025, 1, 3))
    tr_date_list.append(date(2025, 2, 8))
    tr_date_list.append(date(2025, 4, 19))

    # in future
    tr_date_list.append(date(2025, 6, 1))
    tr_date_list.append(date(2025, 6, 2))
    tr_date_list.append(date(2025, 6, 3))
    tr_date_list.append(date(2025, 8, 8))
    tr_date_list.append(date(2026, 1, 1))

    # far past
    tr_date_list.append(date(2020, 1, 1))
    tr_date_list.append(date(2020, 1, 2))
    tr_date_list.append(date(2020, 1, 3))
    tr_date_list.append(date(2023, 8, 8))
    tr_date_list.append(date(2024, 12, 31))

    with uow:
        UtilTest.init_database(uow)
        id_user = uow.user.add(UtilTest.generate_random_string(), UtilTest.generate_random_string())

        uow.app_setting.add(EXC_DATE_CONFIG_NAME, starting_date)

        exc_provider = ExchangeRateProvider()

        from_curr = exc_provider.base_currency

        active_currencies_code = exc_provider._active_currencies

        # Add currencies to the database
        curr_list = get_currency_list(None, None)
        uow.app_setting.add_upd_currency_list(curr_list)

        exc_list = []

        exc_date = date.fromisoformat(starting_date)
        end_date = date.fromisoformat(maximum_date)
        while exc_date <= end_date:
            for curr in active_currencies_code:
                if curr != from_curr:
                    exc = ExchangeRate(
                        from_currency=from_curr,
                        to_currency=curr,
                        rate=random.random() * 3,
                        rate_date=exc_date,
                        is_updated=True,
                    )

                    exc_list.append(exc)

            exc_date += timedelta(days=1)

        uow.exchange_rate.add(exc_list)

    # Add category to the database. We use only one primary with no secondaries since
    # the porpouse of this test is not to control the repository.

    primary = UtilTest.generate_random_string()
    secondary = None

    tr_year_set = set()
    tr_list = []
    for tr_date in tr_date_list:
        tr_list.append(
            TransactionIn(
                id_user=id_user,
                primary=primary,
                secondary=secondary,
                tr_type="expense",
                tr_date=tr_date,
                name=UtilTest.generate_random_string(),
                value=random.random() * 10000,
                currency=random.choice(active_currencies_code),
                description=UtilTest.generate_random_string(),
            )
        )

        tr_year_set.add(tr_date.year)

    cat_list = []
    for tr_year in tr_year_set:
        cat_list.append(
            CategoryIn(
                id_user=id_user,
                year=tr_year,
                category_type="expense",
                primary=primary,
                secondary=secondary,
            )
        )

    with uow:
        uow.category.add(id_user, cat_list)

    tr_service.add_transaction(uow, id_user, tr_list)

    month_year = set()
    for tr_date in tr_date_list:
        year = tr_date.year
        month = tr_date.month
        last_day = calendar.monthrange(year, month)[1]
        month_year = [date(year, month, day) for day in range(1, last_day + 1)]

    with uow:
        for exc_date in month_year:
            exc_get = uow.exchange_rate.get(exc_date)
            assert len(exc_get) == len(active_currencies_code) - 1

            # Dates that will never be updated above those dates since they were not
            # in use from those dates till now
            for exc in exc_get:
                if exc.to_currency == "LVL":
                    if exc.rate_date > date(2014, 2, 1):
                        assert not exc.is_updated

                if exc.to_currency == "LTL":
                    if exc.rate_date > date(2013, 2, 1):
                        assert not exc.is_updated

                if exc.to_currency == "HRK":
                    if exc.rate_date > date(2023, 2, 1):
                        assert not exc.is_updated

                if exc.to_currency == exc.from_currency:
                    raise AssertionError("Same currency for from_currency and to_currency")

    worker.end_worker()


def test_edit_transaction(connection_pool, isolated_worker):
    starting_date = "2025-01-01"
    tr_service = TransactionService()

    uow = UnitOfWork(connection_pool._get_connection())

    primary = UtilTest.generate_random_string()
    secondary = None

    first_date = date(2022, 2, 1)
    edit_date = first_date.replace(year=first_date.year - 1)

    with uow:
        UtilTest.init_database(uow)
        id_user = uow.user.add(UtilTest.generate_random_string(), UtilTest.generate_random_string())
        uow.app_setting.add(EXC_DATE_CONFIG_NAME, starting_date)

        cat_list = []
        cat_list.append(
            CategoryIn(
                id_user=id_user,
                year=first_date.year,
                category_type="expense",
                primary=primary,
                secondary=secondary,
            )
        )
        cat_list.append(
            CategoryIn(
                id_user=id_user,
                year=edit_date.year,
                category_type="expense",
                primary=primary,
                secondary=secondary,
            )
        )

        uow.category.add(id_user, cat_list)

    tr_edit = TransactionIn(
        id_user=id_user,
        primary=primary,
        secondary=None,
        tr_type="expense",
        tr_date=first_date,
        name=UtilTest.generate_random_string(),
        value=random.random() * 10000,
        currency="USD",
        description=UtilTest.generate_random_string(),
    )

    tr_service.add_transaction(uow, id_user, tr_edit)

    tr_get, _ = tr_service.get_transaction(
        uow,
        id_user,
        begin_date=first_date,
        end_date=first_date,
        tr_type="expense",
        primary=primary,
        secondary=secondary,
    )

    tr_get = tr_get[0]

    tr_edit.tr_date = edit_date
    tr_edit.currency = "EUR"

    tr_service.edit_transaction(uow, tr_get.id, tr_edit, id_user)

    with uow:
        exc_get = uow.exchange_rate.get(first_date)
        assert exc_get != []

        exc_get = uow.exchange_rate.get(edit_date)
        assert exc_get != []
