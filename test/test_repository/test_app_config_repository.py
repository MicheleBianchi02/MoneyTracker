import sqlite3

import pytest
from test.util_test import UtilTest

from moneytracker.core.exceptions import DuplicateEntityError
from moneytracker.infrastructure.connection_pool import ConnectionPool
from moneytracker.infrastructure.sqlite.unit_of_work import UnitOfWork


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


def test_add_get_app_config(connection):
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)

        name = "version"
        value = "0-1-1"
        uow.app_config.add(name, value)

        value_get = uow.app_config.get(name)
        assert value == value_get

        name = "date"
        value = "2025-01-01"
        uow.app_config.add(name, value)

        value_get = uow.app_config.get(name)
        assert value == value_get

        # name column must be unique
        try:
            name = "date"
            value = "2025-01-01"
            uow.app_config.add(name, value)

            value_get = uow.app_config.get(name)

        except DuplicateEntityError:
            pass

        # Here we tested also get


def test_edit(connection):
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)

        name = "version"
        value = "0-1-1"
        uow.app_config.add(name, value)

        new_value = "1-0-0"

        uow.app_config.edit(name, new_value)

        new_value_get = uow.app_config.get(name)

        assert new_value == new_value_get


def test_delete(connection):
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)

        name = "version"
        value = "0-1-1"
        uow.app_config.add(name, value)

        uow.app_config.delete(name)

        value_get = uow.app_config.get(name)

        assert value_get is None
