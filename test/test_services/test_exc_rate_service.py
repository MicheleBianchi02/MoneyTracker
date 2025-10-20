import threading
from datetime import date, timedelta
from multiprocessing import Queue
from random import randint, random

import pytest

from moneytracker.core.domain.exchange_rate import ExchangeRate
from moneytracker.core.exceptions import ExchangeRateApiError
from moneytracker.core.services.exc_rate_service import ExchangeRateService
from moneytracker.infrastructure import task_queue, worker
from moneytracker.infrastructure.connection_pool import ConnectionPool
from moneytracker.infrastructure.exchange_rate_provider.exchange_rate import (
    ExchangeRateProvider,
)
from moneytracker.infrastructure.sqlite.unit_of_work import UnitOfWork
from moneytracker.infrastructure.worker import EXC_DATE_CONFIG_NAME
from test.util_test import UtilTest

# TODO: Test what happen when there is no internet connection


@pytest.fixture
def connection_pool(tmp_path) -> ConnectionPool:
    """Create isolated database environment for each test.
    Add tmp_path to the argument to use the tmp directory for the datbase."""

    # tmp_path is a variable internal to pytest. We don't need to define it
    # Create temporary database file
    db_path = tmp_path / "database.db"

    db_path = str(db_path)

    # db_path = ":memory:"  # use in memory database

    return ConnectionPool(db_path, max_connections=2)


@pytest.fixture
def isolated_worker(monkeypatch, connection_pool):
    """Starts a worker with an isolated task queue for each test."""
    q = Queue()
    monkeypatch.setattr(task_queue, "task_queue", q)

    uow_worker = UnitOfWork(connection_pool._get_connection())
    worker_thread = threading.Thread(target=worker.writer_worker, args=(uow_worker,), daemon=False)
    worker_thread.start()

    yield

    worker.end_worker()
    worker_thread.join(timeout=5)


def test_startup_add_from_empty(connection_pool, isolated_worker):
    """Test add exchange rate with empty database"""
    exc_service = ExchangeRateService()

    uow = UnitOfWork(connection_pool._get_connection())

    active_currencies = ExchangeRateService()._active_currencies
    active_currencies_code = [curr.code for curr in active_currencies]
    with uow:
        UtilTest.init_database(uow)

        # Add currencies to the database
        uow.app_config.add_upd_currency_list(active_currencies)

    exc_service.add_exchange_rate(uow)

    with uow:
        max_date = ExchangeRateProvider().maximum_available_date
        st_date = uow.app_config.get(EXC_DATE_CONFIG_NAME)

        assert st_date is not None
        st_date = date.fromisoformat(st_date)

        year = date.today().year
        first_date = date(year, 1, 1)

        day_diff = (date.today() - first_date).days
        if day_diff <= 1:
            first_date = date(year - 1, 1, 1)

        assert first_date == st_date

        date_list = []
        exc_date = st_date
        while exc_date < max_date:
            date_list.append(exc_date)
            exc_date += timedelta(days=1)

        for exc_date in date_list:
            exc_get = uow.exchange_rate.get(exc_date)

            assert len(exc_get) == len(active_currencies_code) - 1

            for exc in exc_get:
                assert exc.to_currency in active_currencies_code


def test_startup_add_from_filled(connection_pool, isolated_worker):
    """Test adding exchange rate when already present in the database but not up to date."""

    exc_service = ExchangeRateService()
    uow = UnitOfWork(connection_pool._get_connection())

    active_currencies = ExchangeRateService()._active_currencies
    active_currencies_code = [curr.code for curr in active_currencies]

    with uow:
        UtilTest.init_database(uow)
        max_date = date(2025, 8, 1)

        st_date = f"{max_date.year}-01-01"
        uow.app_config.add(EXC_DATE_CONFIG_NAME, st_date)
        st_date = date.fromisoformat(st_date)

        date_list = []
        exc_date = st_date
        while exc_date < max_date:
            date_list.append(exc_date)
            exc_date += timedelta(days=1)

        UtilTest.add_exchange_rate(uow, None, date_list)

        # Add currencies to the database
        uow.app_config.add_upd_currency_list(active_currencies)

    exc_service.add_exchange_rate(uow)

    pr_max_date = ExchangeRateProvider().maximum_available_date

    date_list = []
    exc_date = max_date
    while exc_date < pr_max_date:
        date_list.append(exc_date)
        exc_date += timedelta(days=1)

    with uow:
        for exc_date in date_list:
            exc_get = uow.exchange_rate.get(exc_date)

            assert len(exc_get) == len(active_currencies_code) - 1

            for exc in exc_get:
                assert exc.to_currency in active_currencies_code


def test_update(connection_pool, isolated_worker):
    uow = UnitOfWork(connection_pool._get_connection())

    exc_service = ExchangeRateService()
    exc_pr = ExchangeRateProvider()

    from_currency = exc_pr.base_currency

    active_currencies = ExchangeRateService()._active_currencies
    active_currencies_code = [curr.code for curr in active_currencies]
    with uow:
        UtilTest.init_database(uow)

        # Add currencies to the database
        uow.app_config.add_upd_currency_list(active_currencies)

    exc_service.add_exchange_rate(uow)

    with uow:
        # Must be smaller than the maximum date defined in _add_exchange_rate
        max_year = 2023

        n = 10

        date_list = []
        exc_list = []

        for _ in range(n):
            year = randint(2005, max_year)
            exc_date = UtilTest.generate_random_date(year)

            while exc_date in date_list:
                exc_date = UtilTest.generate_random_date(year)

            date_list.append(exc_date)

            for curr in active_currencies_code:
                if curr != from_currency:
                    exc = ExchangeRate(
                        from_currency=from_currency,
                        to_currency=curr,
                        rate=random() * 3,
                        rate_date=exc_date,
                        # is_updated=choice([True, False]),
                        is_updated=False,
                    )

                    exc_list.append(exc)

        uow.exchange_rate.add(exc_list)

    exc_service.update_exchange_rate(uow)

    with uow:
        exc_get = uow.exchange_rate.get_not_updated(None, None)

    curr_dict = {}
    for exc in exc_get:
        curr_dict.setdefault(exc.to_currency, [])
        curr_dict[exc.to_currency].append(exc.rate_date)

    for curr, date_list in curr_dict.items():
        try:
            exc_list, not_available_exc = exc_pr.get_exchange_rate(date_list, curr)
        except ExchangeRateApiError as e:
            assert "Empty Response.content" in str(e)
            # If at first try in _update_exchange_rate the rate were not available, it
            # means that requirind them will return an empty content

