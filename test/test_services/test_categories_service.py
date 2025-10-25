import random
import threading
from datetime import date
from multiprocessing import Queue

import pytest

from moneytracker.core.domain.exchange_rate import Currency
from moneytracker.core.domain.transaction import TransactionOut
from moneytracker.core.exceptions import OperationNotPermittedError
from moneytracker.core.services.category_service import CategoryService
from moneytracker.core.services.transaction_service import TransactionService
from moneytracker.infrastructure import task_queue, worker
from moneytracker.infrastructure.connection_pool import ConnectionPool
from moneytracker.infrastructure.exchange_rate_provider.exchange_rate import ExchangeRateProvider
from moneytracker.infrastructure.sqlite.repositories.app_setting_repository import (
    AppSettingRepostiory,
)
from moneytracker.infrastructure.sqlite.unit_of_work import UnitOfWork
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


def test_delete_cat(connection_pool: ConnectionPool, isolated_worker):
    cat_service = CategoryService()

    uow = UnitOfWork(connection_pool._get_connection())
    with uow:
        UtilTest.init_database(uow)

        user_list, _ = UtilTest.fill_user_cat(uow)

    id_user = random.choice(user_list).id

    sec_list = cat_service.get_secondary_list(uow, id_user, None, None)
    sec = random.choice(sec_list)

    # deleting primary with existing secondaries
    try:
        cat_service.delete(uow, sec.id_primary, id_user)
    except OperationNotPermittedError:
        assert True

    cat_sec_list = cat_service.get_secondary_list(uow, id_user, sec.year, sec.primary)
    for sec in cat_sec_list:
        tr_list = cat_service.delete(uow, sec.id_secondary, id_user)
        assert tr_list is None
        cat_get = cat_service.get(uow, id_user, sec.year, sec.category_type)
        assert sec not in cat_get

    cat_service.delete(uow, sec.id_primary, id_user)
    cat_get = cat_service.get_primary_list(uow, id_user, None, None)
    assert sec.id_primary not in [prim.id_primary for prim in cat_get]


def test_delete_cat_with_tr(connection_pool, isolated_worker):
    curr_list = get_currency_list(None, None)

    def compare_tr(tr_list, tr_get):
        tr_list = sorted(tr_list, key=transaction_sort_key)
        tr_get = sorted(tr_get, key=transaction_sort_key)
        assert tr_list == tr_get

    with UnitOfWork(connection_pool._get_connection()) as uow:
        UtilTest.init_database(uow)

        uow.app_setting.add_upd_currency_list(curr_list)

        _, cat_tot_list, tr_list = UtilTest.fill_user_cat_tr(uow, n_prim=15, n_tr=500)

    tr_service = TransactionService()
    cat_service = CategoryService()

    n = 20
    for _ in range(n):
        cat = random.choice(cat_tot_list)
        cat_list = cat_service.get_secondary_list(uow, cat.id_user, None, None)
        if cat_list:
            cat = random.choice(cat_list)

            begin_date = date(cat.year - 1, 1, 1)
            end_date = date(cat.year + 1, 1, 1)
            tr_list, _ = tr_service.get_transaction(
                uow=uow,
                id_user=cat.id_user,
                begin_date=begin_date,
                end_date=end_date,
                tr_type=cat.category_type,
                primary=cat.primary,
                secondary=cat.secondary,
            )

            tr_list = [tr for tr in tr_list if tr.tr_date.year == cat.year]
            tr_get = cat_service.delete(uow, cat.id_secondary, cat.id_user)
            if tr_list == []:
                assert tr_get is None
            else:
                compare_tr(tr_list, tr_get)

                # cat is not deleted
                cat_get = cat_service.get(uow, cat.id_user, cat.year, cat.category_type)
                assert cat in cat_get


# --- Utils


def transaction_sort_key(tr: TransactionOut) -> tuple:
    """Used to sort a list containing Transaction istances"""

    return (
        tr.id_user,
        tr.primary,
        tr.secondary if tr.secondary is not None else "safdhas",
        tr.tr_type,
        tr.value,
        tr.description,
        tr.currency,
        tr.name,
        tr.tr_date,
    )
