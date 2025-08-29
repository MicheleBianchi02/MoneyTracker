# Run the code below
# pytest test/timing/benchmark_transaction.py --benchmark-autosave


import random
import sqlite3

import pytest

from src.core.domain.transaction import TransactionIn
from src.infrastructure.connection_pool import ConnectionPool
from src.infrastructure.sqlite.initializer import initialize_database
from src.infrastructure.sqlite.unit_of_work import UnitOfWork
from test.util_test import UtilTest


@pytest.fixture
def connection(tmp_path) -> sqlite3.Connection:
    """Create isolated database environment for each test"""
    db_path = tmp_path / "database.db"
    db_path = str(db_path)

    connection_pool = ConnectionPool(db_path, max_connections=1)
    with connection_pool.managed_connection() as connection:
        initialize_database(connection)
        return connection


def test_add_single_transaction(benchmark, connection):
    with UnitOfWork(connection) as uow:
        user_list, _ = UtilTest.fill_user_cat(uow)
        id_user = random.choice(user_list).id
        cat_list = uow.category.get_secondary_list(id_user, None, None)

    cat1 = random.choice(cat_list)
    tr_date = UtilTest.generate_random_date(cat1.year)
    currencies = ["USD", "EUR", "CAD", "GBP", "NZD", "CNY"]

    tr = TransactionIn(
        id_user=id_user,
        primary=cat1.primary,
        secondary=cat1.secondary,
        tr_type=cat1.category_type,
        tr_date=tr_date,
        name=UtilTest.generate_random_string(),
        value=random.random() * 100000,
        description=UtilTest.generate_random_string(),
        currency=random.choice(currencies),
    )

    def f():
        with UnitOfWork(connection) as uow:
            uow.transaction.add(tr)

    benchmark(f)


def test_add_multiple_transaction(benchmark, connection):
    """Adding n_tr to the database."""
    n_tr = 10000

    with UnitOfWork(connection) as uow:
        user_list, _ = UtilTest.fill_user_cat(uow)
        id_user = random.choice(user_list).id
        cat_sec_list = uow.category.get_secondary_list(id_user, None, None)

    currencies = ["USD", "EUR", "CAD", "GBP", "NZD", "CNY"]

    tr_list = []
    for _ in range(n_tr):
        cat1 = random.choice(cat_sec_list)
        id_user = cat1.id_user
        tr_date = UtilTest.generate_random_date(cat1.year)

        tr = TransactionIn(
            id_user=id_user,
            primary=cat1.primary,
            secondary=cat1.secondary,
            tr_type=cat1.category_type,
            tr_date=tr_date,
            name=UtilTest.generate_random_string(),
            value=random.random() * 100000,
            description=UtilTest.generate_random_string(),
            currency=random.choice(currencies),
        )
        tr_list.append(tr)

    benchmark.extra_info["db info"] = f"Adding {n_tr} transactions to the db."

    def f():
        with UnitOfWork(connection) as uow:
            uow.transaction.add(tr_list)

    benchmark(f)


def test_get_all_transactions(benchmark, connection):
    """Get all transaction from the db.
    If only one user is inserted, the number of transaction returned should be n_tr"""

    with UnitOfWork(connection) as uow:
        _, _, tr_list = UtilTest.fill_user_cat_tr(
            uow,
            n_user=3,
            n_prim=20,
            n_tr=900,
        )

    def f():
        with UnitOfWork(connection) as uow:
            return uow.transaction.get(1, None, None)

    tr_get_list = benchmark(f)

    benchmark.extra_info["db info"] = f"{len(tr_list)} transaction present in the db"
    benchmark.extra_info["query"] = "get by user. begin_date = end_date = None"
    benchmark.extra_info["test"] = f"Number of returned transactions : {len(tr_get_list)}"


def test_get_summary(benchmark):
    #
    # with UnitOfWork(connection) as uow:
    #     _, _, tr_list = UtilTest.fill_user_cat_tr(
    #         uow,
    #         n_user=1,
    #         n_prim=20,
    #         n_tr=200,
    #     )
    #
    #     UtilTest.add_exchange_rate(uow, tr_list)
    #

    db_path = "test/timing/benchmark.db"
    conn = sqlite3.connect(db_path)

    with UnitOfWork(conn) as uow:
        user_list = uow.user.get(None)

        # remove duplicate
        id_user_list = {user.id for user in user_list}
        id_user_list = list(id_user_list)

        tr_list = []
        for id_user in id_user_list:
            tr_list += uow.transaction.get(id_user, None, None, "expense")

    begin_date = UtilTest.generate_random_date(2005)

    def f():
        with UnitOfWork(conn) as uow:
            return uow.transaction.get_summary(3, begin_date, None, "expense", "USD")

    tr_get_list, is_updated = benchmark(f)

    benchmark.extra_info["db info"] = f"{len(tr_list)} transactions present in the db"
    benchmark.extra_info["query"] = (
        "get by user. begin_date = end_date = None, tr_type = 'expense', to_currency = 'USD'",
    )
    tr_list = [
        tr
        for tr in tr_list
        if tr.id_user == 3 and tr.tr_type == "expense" and tr.tr_date > begin_date
    ]
    benchmark.extra_info["n_tr"] = f"{len(tr_list)} transaction were used"
