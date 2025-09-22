import random
import sqlite3

import pytest
from test.util_test import UtilTest

from moneytracker.core.domain.category import CategoryIn, CategoryOut
from moneytracker.core.exceptions import ForeignKeyError
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


def test_add_primary_category(connection):
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        user_list = UtilTest.fill_user(uow)
        user = random.choice(user_list)
        id_user = user.id

        year = UtilTest.generate_random_date().year

        # -----------------
        # --- Primary
        primary = UtilTest.generate_random_string()
        cat_prim = CategoryIn(
            year=year,
            category_type="income",
            primary=primary,
            secondary=None,
        )
        uow.category.add(id_user, cat_prim)

        cat_prim.category_type = "expense"
        uow.category.add(id_user, cat_prim)

        cat_get = uow.category.get(id_user, year, "income")[0]
        assert cat_prim.primary == cat_get.primary
        assert cat_prim.secondary == cat_get.secondary

        # Add the same category twice and check if it has been added or not.
        # the correct result should be that the category is not added
        uow.category.add(id_user, cat_prim)

        cat_get = uow.category.get(id_user, year, "expense")
        assert len(cat_get) == 1


def test_add_secondary(connection):
    with UnitOfWork(connection) as uow:
        # new function since if the random year is the same there can be problems

        # -----------------
        # --- Secondary
        UtilTest.init_database(uow)
        user_list = UtilTest.fill_user(uow)
        # Add secondary
        user = random.choice(user_list)
        id_user = user.id

        year = UtilTest.generate_random_date().year

        primary = UtilTest.generate_random_string()
        secondary = UtilTest.generate_random_string()

        cat_sec = CategoryIn(
            year=year,
            category_type="expense",
            primary=primary,
            secondary=secondary,
        )

        secondary2 = UtilTest.generate_random_string()

        cat_sec2 = CategoryIn(
            year=year,
            category_type="expense",
            primary=primary,
            secondary=secondary2,
        )

        uow.category.add(id_user, [cat_sec, cat_sec2])

        cat_get = uow.category.get_primary_list(id_user, year, "expense")
        assert len(cat_get) == 1
        cat_get = cat_get[0]
        assert cat_sec.primary == cat_get.primary

        cat_get = uow.category.get_secondary_list(id_user, year, primary)
        assert len(cat_get) == 2
        assert cat_get[0].primary == primary
        assert cat_get[1].primary == primary
        assert (
            cat_sec.secondary == cat_get[0].secondary or cat_sec.secondary == cat_get[1].secondary
        )
        assert (
            cat_sec2.secondary == cat_get[0].secondary or cat_sec2.secondary == cat_get[1].secondary
        )

        try:
            uow.category.add(232142, cat_sec)

            error = True

        except ForeignKeyError:
            error = False

        if error:
            raise AssertionError("""No error is raised when adding category with 
            id user not present in the database. foreign_key may be disabled""")

        # The DuplicateEntityError is not testable from the repostiory.


def test_get_primary_list_category(connection):
    def compare_prim(cat_list, cat_get):
        """Used only for comparing.
        Since the added category (cat_list) doesn't have category ids we have to
        remove them from the cat_get list."""
        for cat in cat_get:
            cat.id_primary = 0
            if cat.category_type == "income":
                cat.id_secondary = None
            else:
                cat.id_secondary = 0

        cat_get = sorted(cat_get, key=cat_sort_key)
        cat_list = sorted(cat_list, key=cat_sort_key)
        assert cat_list == cat_get

    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        _, cat_list = UtilTest.fill_user_cat(uow)

        # --- get list of all primaries
        cat_prim_list = []
        for cat in cat_list:
            if cat.category_type == "income":
                cat_prim_list.append(cat)

            elif cat.category_type == "expense":
                cat_prim = CategoryOut(
                    id_primary=0,
                    id_secondary=0,
                    id_user=cat.id_user,
                    year=cat.year,
                    category_type="expense",
                    primary=cat.primary,
                    secondary=None,
                )

                if cat_prim not in cat_prim_list:
                    cat_prim_list.append(cat_prim)

        # ---

        n = 10

        for _ in range(n):
            cat1 = random.choice(cat_prim_list)

            id_user = cat1.id_user
            year = cat1.year
            cat_type = cat1.category_type

            # --- get only by user
            cat_comp_list = [cat for cat in cat_prim_list if cat.id_user == id_user]
            cat_get = uow.category.get_primary_list(id_user, None, None)
            compare_prim(cat_comp_list, cat_get)

            # --- get by user and year
            cat_comp_list = [
                cat for cat in cat_prim_list if cat.id_user == id_user and cat.year == year
            ]
            cat_get = uow.category.get_primary_list(id_user, year, None)
            compare_prim(cat_comp_list, cat_get)

            # --- get by user and year and type
            cat_comp_list = [
                cat
                for cat in cat_prim_list
                if cat.id_user == id_user and cat.year == year and cat.category_type == cat_type
            ]
            cat_get = uow.category.get_primary_list(id_user, year, cat_type)
            compare_prim(cat_comp_list, cat_get)

            # get by user and type
            cat_comp_list = [
                cat
                for cat in cat_prim_list
                if cat.id_user == id_user and cat.category_type == cat_type
            ]
            cat_get = uow.category.get_primary_list(id_user, None, cat_type)
            compare_prim(cat_comp_list, cat_get)


def test_get_secondary_list_category(connection):
    def compare_sec(cat_list, cat_get):
        """Used only for comparing.
        Since the added category (cat_list) doesn't have category ids we have to
        remove them from the cat_get list."""
        for cat in cat_get:
            cat.id_primary = 0
            cat.id_secondary = 0

        cat_get = sorted(cat_get, key=cat_sort_key)
        cat_list = sorted(cat_list, key=cat_sort_key)
        assert cat_get == cat_list

    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        _, cat_list = UtilTest.fill_user_cat(uow)

        cat_sec_list = []
        for cat in cat_list:
            if cat.category_type == "expense" and cat.secondary is not None:
                if cat not in cat_sec_list:
                    cat_sec_list.append(cat)

        n = 10

        # TODO: Need a way to check if also the id are correct

        for _ in range(n):
            cat1 = random.choice(cat_list)
            id_user = cat1.id_user

            # using get such that the id_category for the primary are correct
            cat_prim_list = uow.category.get_primary_list(id_user, None, None)

            cat1 = random.choice(cat_prim_list)
            year = cat1.year
            cat_type = cat1.category_type
            primary = cat1.primary

            # get by user
            cat_comp = [cat for cat in cat_sec_list if cat.id_user == id_user]
            cat_get = uow.category.get_secondary_list(id_user, None, None)
            compare_sec(cat_comp, cat_get)

            # get by user and year
            cat_comp = [cat for cat in cat_sec_list if cat.id_user == id_user and cat.year == year]
            cat_get = uow.category.get_secondary_list(id_user, year, None)
            compare_sec(cat_comp, cat_get)

            # get by user and year and primary
            if cat_type != "income":  # income doesn't have secondary
                cat_comp = [
                    cat
                    for cat in cat_sec_list
                    if cat.id_user == id_user and cat.year == year and cat.primary == primary
                ]
                cat_get = uow.category.get_secondary_list(id_user, year, primary)
                compare_sec(cat_comp, cat_get)

            # get by user and primary
            if cat_type != "income":  # income doesn't have secondary
                cat_comp = [
                    cat for cat in cat_sec_list if cat.id_user == id_user and cat.primary == primary
                ]
                cat_get = uow.category.get_secondary_list(id_user, None, primary)
                compare_sec(cat_comp, cat_get)


def test_get_category(connection):
    def compare_cat(cat_list, cat_get):
        """Used only for comparing.
        Since the added category (cat_list) doesn't have category ids we have to
        remove them from the cat_get list."""

        cat_get = sorted(cat_get, key=cat_sort_key)
        cat_list = sorted(cat_list, key=cat_sort_key)
        assert cat_get == cat_list

    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        _, cat_tot_list = UtilTest.fill_user_cat(uow)

        n = 50

        for _ in range(n):
            cat1 = random.choice(cat_tot_list)
            id_user = cat1.id_user
            year = cat1.year
            cat_type = cat1.category_type

            # --- get by user
            cat_prim_list = uow.category.get_primary_list(id_user, None, None)
            cat_sec_list = uow.category.get_secondary_list(id_user, None, None)
            cat_list = cat_prim_list + cat_sec_list
            cat_get = uow.category.get(id_user, None, None)
            compare_cat(cat_list, cat_get)

            # --- get by user and year
            cat_prim_list = uow.category.get_primary_list(id_user, year, None)
            cat_sec_list = uow.category.get_secondary_list(id_user, year, None)
            cat_list = cat_prim_list + cat_sec_list
            cat_get = uow.category.get(id_user, year, None)
            compare_cat(cat_list, cat_get)

            # --- get by user and year and type
            cat_prim_list = uow.category.get_primary_list(id_user, year, cat_type)
            if cat_type == "income":
                cat_sec_list = []
            else:
                cat_sec_list = uow.category.get_secondary_list(id_user, year, None)
            cat_list = cat_prim_list + cat_sec_list
            cat_get = uow.category.get(id_user, year, cat_type)
            compare_cat(cat_list, cat_get)

            # get by user and type
            cat_prim_list = uow.category.get_primary_list(id_user, None, cat_type)
            if cat_type == "income":
                cat_sec_list = []
            else:
                cat_sec_list = uow.category.get_secondary_list(id_user, None, None)
            cat_list = cat_prim_list + cat_sec_list
            cat_get = uow.category.get(id_user, None, cat_type)
            compare_cat(cat_list, cat_get)


def test_get_id_category(connection):
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        _, cat_tot_list = UtilTest.fill_user_cat(uow)

        n = 50

        for _ in range(n):
            cat1 = random.choice(cat_tot_list)
            id_user = cat1.id_user

            # income primary
            cat_inc_list = uow.category.get_primary_list(id_user, None, "income")
            cat_inc = random.choice(cat_inc_list)

            id = uow.category.get_id(
                cat_inc.id_user,
                cat_inc.year,
                cat_inc.category_type,
                cat_inc.primary,
                cat_inc.secondary,
            )
            assert id == cat_inc.id_primary

            # expense primary
            cat_exp_list = uow.category.get_primary_list(id_user, None, "expense")
            cat_exp = random.choice(cat_exp_list)

            id = uow.category.get_id(
                cat_exp.id_user,
                cat_exp.year,
                cat_exp.category_type,
                cat_exp.primary,
                cat_exp.secondary,
            )
            assert id == cat_exp.id_primary

            # expense secondary
            cat_sec_list = uow.category.get_secondary_list(id_user, None, None)
            cat_sec = random.choice(cat_sec_list)

            id = uow.category.get_id(
                cat_sec.id_user,
                cat_sec.year,
                cat_sec.category_type,
                cat_sec.primary,
                cat_sec.secondary,
            )
            assert id == cat_sec.id_secondary


def test_edit_category(connection):
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        _, cat_tot_list = UtilTest.fill_user_cat(uow)

        n = 50

        for _ in range(n):
            cat1 = random.choice(cat_tot_list)
            id_user = cat1.id_user

            cat_inc_edit = uow.category.get_primary_list(id_user, None, "income")
            cat_inc_edit = random.choice(cat_inc_edit)

            cat_inc_edit.primary = UtilTest.generate_random_string()

            uow.category.edit(cat_inc_edit.id_primary, cat_inc_edit.primary)

            cat_get = uow.category.get(
                cat_inc_edit.id_user, cat_inc_edit.year, cat_inc_edit.category_type
            )

            if len(cat_get) == 0:
                raise AssertionError("The category has not been modified")

            for cat in cat_get:
                if cat.id_primary == cat_inc_edit.id_primary:
                    cat_get_edit = cat
                    break

            # check that the name has been modified and the other not
            assert cat_inc_edit.id_user == cat_get_edit.id_user
            assert cat_inc_edit.year == cat_get_edit.year
            assert cat_inc_edit.category_type == cat_get_edit.category_type
            assert cat_inc_edit.primary == cat_get_edit.primary
            assert cat_inc_edit.secondary == cat_get_edit.secondary

            # edit secondary name
            cat_sec_edit = uow.category.get_secondary_list(id_user, None, None)
            cat_sec_edit = random.choice(cat_sec_edit)

            cat_sec_edit.secondary = UtilTest.generate_random_string()

            uow.category.edit(cat_sec_edit.id_secondary, cat_sec_edit.secondary)

            cat_get = uow.category.get(
                cat_sec_edit.id_user, cat_sec_edit.year, cat_sec_edit.category_type
            )

            if len(cat_get) == 0:
                raise AssertionError("The category has not been modified")

            for cat in cat_get:
                if cat.id_secondary == cat_sec_edit.id_secondary:
                    cat_get_edit = cat
                    break

            assert cat_sec_edit.id_user == cat_get_edit.id_user
            assert cat_sec_edit.year == cat_get_edit.year
            assert cat_sec_edit.category_type == cat_get_edit.category_type
            assert cat_sec_edit.primary == cat_get_edit.primary
            assert cat_sec_edit.secondary == cat_get_edit.secondary

            # edit a primary that is parent to some secondaries and check that, after
            # getting them, the name is changed
            cat_sec_edit = uow.category.get_secondary_list(id_user, None, None)
            sec_name_list = [cat.secondary for cat in cat_sec_edit]
            cat_sec_edit = random.choice(cat_sec_edit)

            id_prim = uow.category.get_id(
                id_user,
                cat_sec_edit.year,
                cat_sec_edit.category_type,
                cat_sec_edit.primary,
                None,
            )

            prim_name = UtilTest.generate_random_string()

            uow.category.edit(id_prim, prim_name)

            cat_get = uow.category.get_secondary_list(
                cat_sec_edit.id_user,
                cat_sec_edit.year,
                prim_name,
            )

            if len(cat_get) == 0:
                raise AssertionError("The category has not been modified")

            for cat in cat_get:
                if cat.id_primary == id_prim:
                    cat_get_edit = cat

                    assert cat_sec_edit.id_user == cat_get_edit.id_user
                    assert cat_sec_edit.year == cat_get_edit.year
                    assert cat_sec_edit.category_type == cat_get_edit.category_type
                    assert prim_name == cat_get_edit.primary
                    assert cat_get_edit.secondary in sec_name_list


def test_delete_category(connection):
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        _, cat_tot_list = UtilTest.fill_user_cat(uow, n_prim=400)
        # need 400 because during the test we could delete all the income

        n = 10

        for _ in range(n):
            # delete primary
            cat1 = random.choice(cat_tot_list)
            cat_prim_list = uow.category.get_primary_list(cat1.id_user, None, "income")

            cat_del = random.choice(cat_prim_list)

            uow.category.delete(cat_del.id_primary)

            id = uow.category.get_id(
                cat_del.id_user,
                cat_del.year,
                cat_del.category_type,
                cat_del.primary,
                cat_del.secondary,
            )

            assert id is None

            cat_sec_list = uow.category.get_secondary_list(cat1.id_user, None, None)
            cat_del = random.choice(cat_sec_list)

            uow.category.delete(cat_del.id_secondary)

            id = uow.category.get_id(
                cat_del.id_user,
                cat_del.year,
                cat_del.category_type,
                cat_del.primary,
                cat_del.secondary,
            )

            assert id is None


# --- Utils


def cat_sort_key(cat: CategoryOut) -> tuple:
    """Used to sort a list containing category istances"""
    return (
        cat.id_primary,
        cat.id_secondary if cat.id_secondary is not None else 0,
        cat.id_user,
        cat.year,
        cat.category_type,
        cat.primary,
        cat.secondary if cat.secondary is not None else "dasdasda",
    )
