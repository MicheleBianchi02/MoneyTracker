import random
import sqlite3

import pytest

from src.core.domain.user import User
from src.core.exceptions import DuplicateEntityError
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


def test_add_user(connection: str) -> None:
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        username = UtilTest.generate_random_string()
        password = UtilTest.generate_random_string()

        id_user = uow.user.add(username, password)

        assert id_user == 1

        # check that username is unique
        try:
            _ = uow.user.add(username, UtilTest.generate_random_string())

            error = True

        except DuplicateEntityError:
            error = False

        if error:
            raise AssertionError(
                """No error is raised when adding two user with the same username. 
                UNIQUE value on it may not be activated"""
            )


def test_get_user(connection: str):
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        user_list = UtilTest.fill_user(uow, n_user=100)
        n = 100

        for _ in range(n):
            user = random.choice(user_list)

            user_get = uow.user.get(user.username)
            assert user_get[0] == user

            user_get_list = uow.user.get(None)
            user_get_list = sorted(user_get_list, key=user_sort_key)

            assert sorted(user_list, key=user_sort_key) == user_get_list


def test_edit_user(connection: str) -> None:
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        user_list = UtilTest.fill_user(uow, n_user=100)
        n = 100

        for _ in range(n):
            user_edit = random.choice(user_list)

            username = UtilTest.generate_random_string()

            # Check if the username is unique, otherwise we would get an error
            # from the database. This is not so usefull if the random string is
            # sufficiently long
            username_unique = False
            idx = 0
            while not username_unique and len(user_list) != 0:
                if username == user_list[idx].username:
                    username = UtilTest.generate_random_string()
                    idx = 0  # Restart the loop

                else:
                    if len(user_list) - 1 == idx:
                        username_unique = True

                    idx += 1

            user_edit.username = username
            user_edit.password = UtilTest.generate_random_string()

            uow.user.edit(user_edit)

            user_get = uow.user.get(username=user_edit.username)
            assert user_get[0] == user_edit

            try:
                # can't add a new
                user_get = uow.user.get(None)

                user_edit = random.choice(user_get)
                user_edit_1 = random.choice(user_get)

                user_edit.username = user_edit_1.username
                uow.user.edit(user_edit)  # the id should be the same

            except DuplicateEntityError:
                assert True


def test_delete_user(connection):
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        user_list, _, _ = UtilTest.fill_user_cat_tr(uow, n_user=100)

        for _ in range(10):
            user_list = uow.user.get(None)
            user = random.choice(user_list)
            id_user = user.id
            uow.user.delete(id_user)

            # Because of foreign key, every category and transaction with the same id_user
            # should be deleted

            user_get = uow.user.get(user.username)
            assert user_get == []

            cat_get = uow.category.get(id_user, None, None)
            assert cat_get == []

            tr_get = uow.transaction.get(id_user, None, None)
            assert tr_get == []

            # settings are checked in the setting test's script


# utils
def user_sort_key(user: User) -> tuple:
    """Used for sorting list of Users"""

    return (
        user.username,
        user.password,
    )
