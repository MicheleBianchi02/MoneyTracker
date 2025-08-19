import pytest

from src.core.exceptions import UsernameAlreadyPresentError
from src.core.services.user_service import UserService
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


def test_add_user(db_env):
    uow = UnitOfWork(db_env)

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


def test_authenticate(db_env):
    uow = UnitOfWork(db_env)

    user_service = UserService()

    username = UtilTest.generate_random_string()
    password = UtilTest.generate_random_string()

    with uow:
        UtilTest.init_database(uow)

    user_service.add(uow, username, password)

    is_auth = user_service.authenticate(uow, username, password)
    assert is_auth

    is_auth = user_service.authenticate(uow, username, UtilTest.generate_random_string())
    assert not is_auth


def test_edit(db_env):
    uow = UnitOfWork(db_env)

    user_service = UserService()

    username = UtilTest.generate_random_string()
    password = UtilTest.generate_random_string()

    with uow:
        UtilTest.init_database(uow)

    user_service.add(uow, username, password)

    new_password = UtilTest.generate_random_string()

    new_user = user_service.get(uow, username)[0]
    new_user.password = new_password

    user_service.edit(uow, new_user)

    is_aut = user_service.authenticate(uow, username, new_password)
    assert is_aut

    is_aut = user_service.authenticate(uow, username, password)
    assert not is_aut
