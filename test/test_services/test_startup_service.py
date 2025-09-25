import threading
from datetime import date, timedelta
from random import randint, random

import pytest

from moneytracker.core.domain.exchange_rate import ExchangeRate
from moneytracker.core.exceptions import ExchangeRateApiError
from moneytracker.core.services.startup import (
    EXC_DATE_CONFIG_NAME,
    _add_exchange_rate,
    _update_exchange_rate,
)
from moneytracker.infrastructure import worker
from moneytracker.infrastructure.connection_pool import ConnectionPool
from moneytracker.infrastructure.exchange_rate_provider.exchange_rate import ExchangeRateProvider
from moneytracker.infrastructure.sqlite.unit_of_work import UnitOfWork
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


def test_startup_add_from_empty(connection_pool):
    """Test add exchange rate with empty database"""
    uow_worker = UnitOfWork(connection_pool._get_connection())
    threading.Thread(target=worker.writer_worker, args=(uow_worker,), daemon=False).start()

    uow = UnitOfWork(connection_pool._get_connection())

    with uow:
        UtilTest.init_database(uow)

    _add_exchange_rate(uow)

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

            assert len(exc_get) == len(ExchangeRateProvider().available_currencies) - 1

    worker.end_worker()


def test_startup_add_from_filled(connection_pool):
    """Test adding exchange rate when already present in the database but not up to date."""
    uow_worker = UnitOfWork(connection_pool._get_connection())
    threading.Thread(target=worker.writer_worker, args=(uow_worker,), daemon=False).start()

    uow = UnitOfWork(connection_pool._get_connection())

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

    _add_exchange_rate(uow)

    pr_max_date = ExchangeRateProvider().maximum_available_date

    date_list = []
    exc_date = max_date
    while exc_date < pr_max_date:
        date_list.append(exc_date)
        exc_date += timedelta(days=1)

    with uow:
        for exc_date in date_list:
            exc_get = uow.exchange_rate.get(exc_date)

            assert len(exc_get) == len(ExchangeRateProvider().available_currencies) - 1

    worker.end_worker()


def test_update(connection_pool):
    uow_worker = UnitOfWork(connection_pool._get_connection())
    threading.Thread(target=worker.writer_worker, args=(uow_worker,), daemon=False).start()

    uow = UnitOfWork(connection_pool._get_connection())

    exc_pr = ExchangeRateProvider()

    from_currency = exc_pr.base_currency
    available_currencies = exc_pr.available_currencies

    with uow:
        UtilTest.init_database(uow)

    _add_exchange_rate(uow)

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

            for curr in available_currencies:
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

    _update_exchange_rate(uow)

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
    worker.end_worker()
