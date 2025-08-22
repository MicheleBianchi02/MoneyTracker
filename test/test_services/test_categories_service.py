import random

import pytest

from src.core.exceptions import OperationNotPermittedError
from src.core.services.category_service import CategoryService
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


# TODO: Add the control on the transactions
