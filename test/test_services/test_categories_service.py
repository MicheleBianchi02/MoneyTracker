import random
from datetime import date

import pytest

from src.core.domain.transaction import TransactionOut
from src.core.exceptions import OperationNotPermittedError
from src.core.services.category_service import CategoryService
from src.core.services.transaction_service import TransactionService
from src.infrastructure.sqlite.unit_of_work import UnitOfWork
from test.util_test import UtilTest


@pytest.fixture
def db_env(tmp_path) -> str:
    """Create isolated database environment for each test.
    Add tmp_path to the argument to use the tmp directory for the datbase."""

    # tmp_path is a variable internal to pytest. We don't need to define it
    # Create temporary database file
    db_path = tmp_path / "database.db"

    db_path = str(db_path)

    # db_path = ":memory:"  # use in memory database

    return db_path


def test_delete_cat(db_env):
    db_path = db_env

    cat_service = CategoryService()

    uow = UnitOfWork(db_path)
    with uow:
        UtilTest.init_database(uow)

        user_list, _ = UtilTest.fill_user_cat(uow)

    id_user = random.choice(user_list).id

    sec_list = cat_service.get_secondary_list(uow, id_user, None, None)
    sec = random.choice(sec_list)

    try:
        cat_service.delete(uow, sec.id_primary)
    except OperationNotPermittedError:
        assert True

    tr_list = cat_service.delete(uow, sec.id_secondary)
    assert tr_list is None
    cat_get = cat_service.get(uow, sec.id_user, sec.year, sec.category_type)
    assert sec not in cat_get


def test_delete_cat_with_tr(db_env):
    def compare_tr(tr_list, tr_get):
        tr_list = sorted(tr_list, key=transaction_sort_key)
        tr_get = sorted(tr_get, key=transaction_sort_key)
        assert tr_list == tr_get

    db_path = db_env
    tr_service = TransactionService()
    cat_service = CategoryService()

    with UnitOfWork(db_path) as uow:
        UtilTest.init_database(uow)
        _, cat_tot_list, tr_list = UtilTest.fill_user_cat_tr(uow, n_prim=15, n_tr=500)

    n = 20
    for _ in range(n):
        cat = random.choice(cat_tot_list)
        cat_list = cat_service.get_secondary_list(uow, cat.id_user, None, None)
        if cat_list:
            cat = random.choice(cat_list)

            begin_date = date(cat.year - 1, 1, 1)
            end_date = date(cat.year + 1, 1, 1)
            tr_list = tr_service.get_transaction(
                uow=uow,
                id_user=cat.id_user,
                begin_date=begin_date,
                end_date=end_date,
                tr_type=cat.category_type,
                primary=cat.primary,
                secondary=cat.secondary,
            )

            tr_list = [tr for tr in tr_list if tr.tr_date.year == cat.year]
            tr_get = cat_service.delete(uow, cat.id_secondary)
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
