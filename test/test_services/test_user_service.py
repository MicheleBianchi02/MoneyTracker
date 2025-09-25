import threading

import pytest

from moneytracker.core.exceptions import UsernameAlreadyPresentError
from moneytracker.core.services.user_service import UserService
from moneytracker.infrastructure import worker
from moneytracker.infrastructure.connection_pool import ConnectionPool
from moneytracker.infrastructure.sqlite.unit_of_work import UnitOfWork
from test.util_test import UtilTest


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


def test_add_user(connection_pool):
    uow_worker = UnitOfWork(connection_pool._get_connection())
    threading.Thread(target=worker.writer_worker, args=(uow_worker,), daemon=False).start()

    uow = UnitOfWork(connection_pool._get_connection())

    user_service = UserService()

    username = UtilTest.generate_random_string()
    password = UtilTest.generate_random_string()

    with uow:
        UtilTest.init_database(uow)

    user_service.add(uow, username, password)
    try:
        user_service.add(uow, username, password)
    except UsernameAlreadyPresentError:
        assert True

    with uow:
        user = uow.user.get(username)[0]

        assert username == user.username
        assert "$argon2id$" in user.password

    worker.end_worker()


def test_authenticate(connection_pool):
    uow_worker = UnitOfWork(connection_pool._get_connection())
    threading.Thread(target=worker.writer_worker, args=(uow_worker,), daemon=False).start()

    uow = UnitOfWork(connection_pool._get_connection())

    user_service = UserService()

    username = UtilTest.generate_random_string()
    password = UtilTest.generate_random_string()

    with uow:
        UtilTest.init_database(uow)

    user_service.add(uow, username, password)

    user = user_service.authenticate(uow, username, password)
    assert user is not None

    user = user_service.authenticate(uow, username, UtilTest.generate_random_string())
    assert user is None

    worker.end_worker()


def test_edit(connection_pool):
    uow_worker = UnitOfWork(connection_pool._get_connection())
    threading.Thread(target=worker.writer_worker, args=(uow_worker,), daemon=False).start()

    uow = UnitOfWork(connection_pool._get_connection())

    user_service = UserService()

    username = UtilTest.generate_random_string()
    password = UtilTest.generate_random_string()

    with uow:
        UtilTest.init_database(uow)

    user_service.add(uow, username, password)

    new_password = UtilTest.generate_random_string()

    new_user = user_service.get(uow, username)[0]

    user_service.edit(uow, new_user.id, None, new_password, password)

    user = user_service.authenticate(uow, username, new_password)
    assert user is not None

    user = user_service.authenticate(uow, username, password)
    assert user is None

    worker.end_worker()
