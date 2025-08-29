import random
import sqlite3
from datetime import date

import pytest

from src.core.domain.exchange_rate import ExchangeRate
from src.core.exceptions import InvalidParameterError
from src.infrastructure.connection_pool import ConnectionPool
from src.infrastructure.sqlite.unit_of_work import UnitOfWork
from test.util_test import UtilTest


# NOTE: Currently every test function is calling this function creating a new database,
# no error is raised, only warning. This is needed because at every test a clean
# database is needed
@pytest.fixture
def connection() -> sqlite3.Connection:
    """Create isolated database environment for each test.
    Add tmp_path to the argument to use the tmp directory for the datbase."""

    # tmp_path is a variable internal to pytest. We don't need to define it
    # Create temporary database file
    # db_path = tmp_path / "database.db"
    #
    # db_path = str(db_path)

    db_path = ":memory:"  # use in memory database

    connection_pool = ConnectionPool(db_path, max_connections=1)
    with connection_pool.managed_connection() as connection:
        return connection


def test_add_exchange_rate(connection) -> None:
    currencies = UtilTest.currencies

    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        _, _, tr_list = UtilTest.fill_user_cat_tr(uow, n_tr=100)

        date_list = []
        for tr in tr_list:
            if tr.tr_date not in date_list:
                date_list.append(tr.tr_date)

        exc_list = []
        for tr_date in date_list:
            # from currency must be the same for all exchange rate in the same date
            from_currency = random.choice(currencies)

            for currency in currencies:
                if currency != from_currency:
                    exc = ExchangeRate(
                        from_currency=from_currency,
                        to_currency=currency,
                        rate=random.random() * 3,
                        rate_date=tr_date,
                        is_updated=random.choice([True, False]),
                    )

                    if exc not in exc_list:
                        exc_list.append(exc)

        uow.exchange_rate.add(exc_list)

        for exc in exc_list:
            exc_get = uow.exchange_rate.get(
                exc.rate_date,
                from_currency=exc.from_currency,
                to_currency=exc.to_currency,
            )

            assert exc == exc_get[0]

        try:
            exc = ExchangeRate(
                from_currency="EUR",
                to_currency="EUR",
                rate=1,
                rate_date=date(2025, 1, 1),
                is_updated=True,
            )

            uow.exchange_rate.add(exc)
        except InvalidParameterError:
            assert True


def test_get_exchange_rate(connection) -> None:
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)

        _, _, tr_list = UtilTest.fill_user_cat_tr(uow, n_tr=500)
        exc_ret_list = UtilTest.add_exchange_rate(uow, tr_list)

        n = 20

        for _ in range(n):
            exc = random.choice(exc_ret_list)
            exc_date = exc.rate_date
            from_currency = exc.from_currency
            to_currency = exc.to_currency

            exc_list = [exc for exc in exc_ret_list if exc.rate_date == exc_date]
            exc_get = uow.exchange_rate.get(exc.rate_date, None, None)
            compare_exc(exc_list, exc_get)

            exc_list = [
                exc
                for exc in exc_ret_list
                if exc.from_currency == from_currency and exc.rate_date == exc_date
            ]
            exc_get = uow.exchange_rate.get(exc_date, from_currency, None)
            compare_exc(exc_list, exc_get)

            exc_list = [
                exc
                for exc in exc_ret_list
                if exc.to_currency == to_currency and exc.rate_date == exc_date
            ]
            exc_get = uow.exchange_rate.get(exc_date, None, to_currency)
            compare_exc(exc_list, exc_get)

            exc_list = [
                exc
                for exc in exc_ret_list
                if exc.from_currency == from_currency
                and exc.to_currency == to_currency
                and exc.rate_date == exc_date
            ]
            exc_get = uow.exchange_rate.get(exc_date, from_currency, to_currency)
            compare_exc(exc_list, exc_get)


def test_get_closest_exchange_rate(connection):
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        _, _, tr_list = UtilTest.fill_user_cat_tr(uow, n_tr=100)

        cl_date = UtilTest.generate_random_date()
        cl_exc_get = uow.exchange_rate.get_closest(cl_date)

        assert cl_exc_get == []

        exc_ret_list = UtilTest.add_exchange_rate(uow, tr_list)

        n = 10

        for _ in range(n):
            cl_date = UtilTest.generate_random_date()

            cl_exc = min(exc_ret_list, key=lambda d: abs(d.rate_date - cl_date))
            exc_list = [exc for exc in exc_ret_list if exc.rate_date == cl_exc.rate_date]

            cl_exc_get = uow.exchange_rate.get_closest(cl_date)

            # When there are two dates with the same days difference, exc_list and cl_exc_get
            # may be different. This is not an error because the order in which the
            # list is scanned may be different. In those cases we assume that the result
            # is correct.
            if cl_exc.rate_date != cl_exc_get[0].rate_date:
                if abs(cl_exc.rate_date - cl_date) == abs(cl_exc_get[0].rate_date - cl_date):
                    assert True

                else:
                    raise AssertionError("get_closest method returned wrong result")

            else:
                compare_exc(exc_list, cl_exc_get)


def test_get_not_update(connection):
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        _, _, tr_list = UtilTest.fill_user_cat_tr(uow, n_tr=100)

        exc_ret_list = UtilTest.add_exchange_rate(uow, tr_list)

        n = 20

        for _ in range(n):
            exc_list = [exc for exc in exc_ret_list if not exc.is_updated]
            exc_get = uow.exchange_rate.get_not_updated(None, None)
            compare_exc(exc_list, exc_get)

            begin_date = date(2015, 1, 1)
            exc_list = [
                exc for exc in exc_ret_list if not exc.is_updated and exc.rate_date >= begin_date
            ]
            exc_get = uow.exchange_rate.get_not_updated(begin_date, None)
            compare_exc(exc_list, exc_get)

            end_date = date(2020, 1, 1)
            exc_list = [
                exc for exc in exc_ret_list if not exc.is_updated and exc.rate_date <= end_date
            ]
            exc_get = uow.exchange_rate.get_not_updated(None, end_date)
            compare_exc(exc_list, exc_get)

            exc_list = [
                exc
                for exc in exc_ret_list
                if not exc.is_updated and exc.rate_date >= begin_date and exc.rate_date <= end_date
            ]
            exc_get = uow.exchange_rate.get_not_updated(begin_date, end_date)
            compare_exc(exc_list, exc_get)


def test_get_missing_rates_dates(connection):
    currencies = UtilTest.currencies

    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)

        n_date = 300
        date_list = []
        for _ in range(n_date):
            exc_date = UtilTest.generate_random_date()
            while exc_date in date_list:
                exc_date = UtilTest.generate_random_date()
            date_list.append(exc_date)

        exc_list = []
        for exc_date in date_list:
            from_currency = random.choice(currencies)
            for curr in currencies:
                if curr != from_currency:
                    exc = ExchangeRate(
                        from_currency=from_currency,
                        to_currency=curr,
                        rate=random.random(),
                        rate_date=exc_date,
                        is_updated=True,
                    )

                    exc_list.append(exc)

        uow.exchange_rate.add(exc_list)

        n_wrong_date = 10000
        wrong_date_list = []
        for _ in range(n_wrong_date):
            exc_date = UtilTest.generate_random_date()
            while exc_date in date_list:
                exc_date = UtilTest.generate_random_date()

            wrong_date_list.append(exc_date)

        missing_date = uow.exchange_rate.get_missing_rates_dates(date_list + wrong_date_list)

        wrong_date_list = list(set(wrong_date_list))

        assert sorted(wrong_date_list) == sorted(missing_date)


def test_edit_exchange_rate(connection):
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        _, _, tr_list = UtilTest.fill_user_cat_tr(uow, n_tr=50)

        exc_ret_list = UtilTest.add_exchange_rate(uow, tr_list)

        n = 15

        for _ in range(n):
            exc_ed = random.choice(exc_ret_list)

            exc_ed.rate = random.random() * 3
            exc_ed.is_updated = False if exc_ed.is_updated else True

            uow.exchange_rate.edit(exc_ed)

            exc_get = uow.exchange_rate.get(
                exc_ed.rate_date,
                exc_ed.from_currency,
                exc_ed.to_currency,
            )

            assert exc_ed == exc_get[0]


def test_delete_exchange_rate(connection):
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        _, _, tr_list = UtilTest.fill_user_cat_tr(uow, n_tr=50)

        _ = UtilTest.add_exchange_rate(uow, tr_list)

        n = 20

        for _ in range(n):
            # we don't do random.choice(exc_ret_list) since some of them get deleted
            cl_date = UtilTest.generate_random_date()
            exc_list = uow.exchange_rate.get_closest(cl_date)
            exc = random.choice(exc_list)

            uow.exchange_rate.delete(exc)

            exc_get = uow.exchange_rate.get(exc.rate_date, exc.from_currency, exc.to_currency)

            assert exc_get == []


# Utils
def exc_sort_key(exc: ExchangeRate) -> tuple:
    """Keys used in the function sorted."""
    return (
        exc.from_currency,
        exc.to_currency,
        exc.rate,
        exc.rate_date,
    )


def compare_exc(exc_list, exc_get):
    exc_list = sorted(exc_list, key=exc_sort_key)
    exc_get = sorted(exc_get, key=exc_sort_key)

    assert exc_list == exc_get
