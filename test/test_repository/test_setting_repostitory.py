import random
import sqlite3

import pytest
from test.util_test import UtilTest

from moneytracker import default_settings
from moneytracker.core.domain.setting import Setting
from moneytracker.core.exceptions import DuplicateEntityError, ForeignKeyError
from moneytracker.infrastructure.connection_pool import ConnectionPool
from moneytracker.infrastructure.sqlite.repositories.user_settings_repository import _convert_value
from moneytracker.infrastructure.sqlite.unit_of_work import UnitOfWork


@pytest.fixture
def connection(tmp_path) -> sqlite3.Connection:
    """Create isolated database environment for each test.
    Add tmp_path to the argument to use the tmp directory for the datbase."""

    # tmp_path is a variable internal to pytest. We don't need to define it
    # Create temporary database file
    db_path = tmp_path / "database.db"

    db_path = str(db_path)

    connection_pool = ConnectionPool(db_path, max_connections=1)
    with connection_pool.managed_connection() as connection:
        return connection


@pytest.fixture
def setting_list() -> list[Setting]:
    setting_list = []
    for sett in default_settings.SETTINGS_DATA:
        setting_list.append(
            Setting(
                id_setting=0,
                name=sett["name"],
                constrained=True if sett["constrained"] == 1 else False,
                allowed_settings=sett["allowed_settings"],
                value=_convert_value(sett["data_type"], sett["default"]),
            )
        )

    return setting_list


def test_fill_table_setting(connection, setting_list):
    """Test if filling the database two time with the same connection will create
    problems."""

    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)

        sett_get = uow.user_setting.get(None)
        compare_sett(setting_list, sett_get)

        UtilTest.init_database(uow)
        sett_get = uow.user_setting.get(None)
        compare_sett(setting_list, sett_get)


def test_add_setting(connection, setting_list: list[Setting]):
    n = 10

    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        user_list = UtilTest.fill_user(uow)

        # Doing it n times we also check if update is working
        for _ in range(n):
            id_user = random.choice(user_list).id
            for sett in setting_list:
                if sett.constrained:
                    all = random.choice(sett.allowed_settings)
                    value = all["item_value"]
                    sett.value = value

                else:
                    if isinstance(sett.value, bool):
                        value = random.choice([True, False])
                    elif isinstance(sett.value, int):
                        value = random.randint(1, 6)
                    elif isinstance(sett.value, float):
                        value = random.random() * 100
                    else:
                        value = UtilTest.generate_random_string()

                    sett.value = value

                uow.user_setting.add(id_user, sett.name, value)

            sett_get = uow.user_setting.get(id_user, None)
            compare_sett(setting_list, sett_get)


def test_get_setting(connection, setting_list: list[Setting]):
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)

        sett_get = uow.user_setting.get(None)
        compare_sett(setting_list, sett_get)

        setting = random.choice(setting_list)
        sett_get = uow.user_setting.get(None, setting.name)
        compare_sett([setting], sett_get)

        user_list, user_sett_list = UtilTest.fill_user_setting(uow, setting_list)
        for user in user_list:
            id_user = user.id
            sett_get = uow.user_setting.get(id_user, None)
            compare_sett(user_sett_list[str(id_user)], sett_get)

            setting = random.choice(user_sett_list[str(id_user)])
            sett_get = uow.user_setting.get(id_user, setting.name)
            compare_sett([setting], sett_get)


def test_add_currency_setting(connection, setting_list) -> None:
    currencies = [("USD", "$"), ("EUR", "€"), ("CAD", None), ("GBP", "£"), ("NZD", None)]
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        user_list, _ = UtilTest.fill_user_setting(uow, setting_list)
        user = random.choice(user_list)

        currency = random.choice(currencies)
        uow.user_setting.add_currency(user.id, currency[0], currency[1])
        # currencies are unique for each user
        try:
            error = False
            uow.user_setting.add_currency(user.id, currency[0], currency[1])
        except DuplicateEntityError:
            error = True
        finally:
            if not error:
                raise AssertionError(
                    "No error has been raised when inserting the same currency",
                )

        # check foreign key
        id_user = 20341232
        try:
            uow.user_setting.add_currency(id_user, currency[0], currency[1])
            error = True

        except ForeignKeyError:
            error = False

        if error:
            raise AssertionError("""No error is raised when adding currency with 
            id user not present in the database. foreign_key may be disabled""")


def test_get_currencies_setting(connection) -> None:
    currencies = [("USD", "$"), ("EUR", "€"), ("CAD", None), ("GBP", "£"), ("NZD", None)]
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        user_list = UtilTest.fill_user(uow)
        for user in user_list:
            id_user = user.id

            for currency in currencies:
                uow.user_setting.add_currency(id_user, currency[0], currency[1])

            curr_get = uow.user_setting.get_currency_list(id_user)
            assert len(currencies) == len(curr_get)
            for curr in curr_get:
                assert curr in currencies


def test_delete_currency_setting(connection) -> None:
    currencies = [("USD", "$"), ("EUR", "€"), ("CAD", None), ("GBP", "£"), ("NZD", None)]
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        user_list = UtilTest.fill_user(uow)
        for user in user_list:
            id_user = user.id

            for currency in currencies:
                uow.user_setting.add_currency(id_user, currency[0], currency[1])

        curr_del = random.choice(currencies)
        uow.user_setting.delete_currency(id_user, curr_del[0])

        curr_get = uow.user_setting.get_currency_list(id_user)
        assert curr_del not in curr_get


def test_delete_user_setting(connection, setting_list):
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)

        user_list, _ = UtilTest.fill_user_setting(uow, setting_list)

        for user in user_list:
            id_user = user.id
            user_list, user_sett_list = UtilTest.fill_user_setting(uow, setting_list)

            uow.user.delete(id_user)

            # we can't just use uow.user_setting.get because, when the id_user is not present
            # in that table, the default value is returned.

            cursor = uow.connection.cursor()

            sql = f"""
                SELECT
                    *
                FROM 
                    user_settings
                WHERE
                    id_user = {id_user}
            """

            sett_get = cursor.execute(sql).fetchall()

            assert sett_get == []


# --- Utils
def sett_sort_key(sett: Setting) -> tuple:
    return (
        # str(sett.value),
        sett.name,
        sett.allowed_settings.sort(key=lambda x: x["item_value"]),  # sort the dict
        # str(sett.constrained),
    )


def compare_sett(sett_list, sett_get):
    for sett in sett_get:
        sett.id_setting = 0

    sett_list = sorted(sett_list, key=sett_sort_key)
    sett_get = sorted(sett_get, key=sett_sort_key)
    assert sett_list == sett_get
