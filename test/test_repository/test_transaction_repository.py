import random
from datetime import date

import pytest

from src.core.domain.transaction import TransactionIn, TransactionOut
from src.core.exceptions import EntityNotFoundError
from src.infrastructure.sqlite.unit_of_work import UnitOfWork
from test.util_test import UtilTest


# NOTE: Currently every test function is calling this function creating a new database,
# no error is raised, only warning. This is needed because at every test a clean
# database is needed
@pytest.fixture
def db_env() -> str:
    """Create isolated database environment for each test.
    Add tmp_path to the argument to use the tmp directory for the datbase."""

    # tmp_path is a variable internal to pytest. We don't need to define it
    # Create temporary database file
    # db_path = tmp_path / "database.db"
    #
    # db_path = str(db_path)

    db_path = ":memory:"  # use in memory database

    return db_path


def test_add_transaction(db_env: str) -> None:
    db_path = db_env

    currencies = UtilTest.currencies

    with UnitOfWork(db_path) as uow:
        UtilTest.init_database(uow)
        _, cat_list = UtilTest.fill_user_cat(uow)
        cat1 = random.choice(cat_list)

        # --- add income
        cat_list = uow.category.get_primary_list(cat1.id_user, None, "income")
        cat1 = random.choice(cat_list)

        tr_date = UtilTest.generate_random_date(cat1.year)

        tr = TransactionIn(
            id_user=cat1.id_user,
            primary=cat1.primary,
            secondary=cat1.secondary,
            tr_type=cat1.category_type,
            tr_date=tr_date,
            name=UtilTest.generate_random_string(),
            value=random.random() * 10000,
            currency=random.choice(currencies),
            description=UtilTest.generate_random_string(),
        )

        uow.transaction.add(tr)

        # --- add expense
        cat_list = uow.category.get_secondary_list(cat1.id_user, None, None)
        cat1 = random.choice(cat_list)

        tr_date = UtilTest.generate_random_date(cat1.year)

        tr = TransactionIn(
            id_user=cat1.id_user,
            primary=cat1.primary,
            secondary=cat1.secondary,
            tr_type=cat1.category_type,
            tr_date=tr_date,
            name=UtilTest.generate_random_string(),
            value=random.random() * 10000,
            currency=random.choice(currencies),
            description=UtilTest.generate_random_string(),
        )

        uow.transaction.add(tr)

        # check foreign key
        tr.id_user = 20341232
        try:
            uow.transaction.add(tr)
            error = True

        except Exception:
            error = False

        if error:
            raise AssertionError("""No error is raised when adding transaction with 
            id user not present in the database. foreign_key may be disabled""")


def test_get_transaction(db_env):
    def compare_tr(tr_list, tr_get):
        for tr in tr_get:
            tr.id = 0

        tr_list = sorted(tr_list, key=transaction_sort_key)
        tr_get = sorted(tr_get, key=transaction_sort_key)
        assert tr_list == tr_get

    db_path = db_env

    with UnitOfWork(db_path) as uow:
        UtilTest.init_database(uow)
        _, cat_list, tr_tot_list = UtilTest.fill_user_cat_tr(uow, n_tr=1000)
        n = 25
        # not just one becouse for some test i need to check on bothj income and expense

        for _ in range(n):
            tr1 = random.choice(tr_tot_list)
            id_user = tr1.id_user
            tr_date = tr1.tr_date

            # -----------
            # --- by user
            tr_list = [tr for tr in tr_tot_list if tr.id_user == id_user]
            tr_get = uow.transaction.get(id_user, None, None)
            compare_tr(tr_list, tr_get)

            # --- by user, begin_date
            tr_list = [tr for tr in tr_tot_list if tr.id_user == id_user and tr.tr_date >= tr_date]
            tr_get = uow.transaction.get(id_user, tr_date, None)
            compare_tr(tr_list, tr_get)

            # --- by user, end_date
            tr_list = [tr for tr in tr_tot_list if tr.id_user == id_user and tr.tr_date <= tr_date]
            tr_get = uow.transaction.get(id_user, None, tr_date)
            compare_tr(tr_list, tr_get)

            # --- by user, begin_date, end_date (2 year interval)
            begin_date = tr_date.replace(year=tr_date.year - 1, month=1, day=1)
            end_date = tr_date.replace(year=tr_date.year + 1, month=1, day=1)

            tr_list = [
                tr
                for tr in tr_tot_list
                if tr.id_user == id_user and tr.tr_date >= begin_date and tr.tr_date <= end_date
            ]
            tr_get = uow.transaction.get(id_user, begin_date, end_date)
            compare_tr(tr_list, tr_get)

            # ------------------------
            # ------------------------
            # by user, type = 'income'
            tr_list = []
            cat_prim_list = uow.category.get_primary_list(id_user, None, "income")
            for cat in cat_prim_list:
                for tr in tr_tot_list:
                    if (
                        tr.primary == cat.primary
                        and tr.tr_date.year == cat.year
                        and tr.tr_type == "income"
                    ):
                        tr_list.append(tr)

            tr_get = uow.transaction.get(id_user, None, None, tr_type="income")
            compare_tr(tr_list, tr_get)

            cat1 = random.choice(cat_prim_list)
            tr_list = [tr for tr in tr_list if tr.primary == cat1.primary]

            # -------------------------
            # -------------------------
            # by user, type = 'expense'
            tr_list = []
            # expenses may not have secondaries (like incomes)
            cat_prim_list = uow.category.get_primary_list(id_user, None, "expense")
            cat_sec_list = uow.category.get_secondary_list(id_user, None, None)
            cat_list = cat_prim_list + cat_sec_list
            for cat in cat_list:
                for tr in tr_tot_list:
                    if (
                        tr.primary == cat.primary
                        and tr.tr_date.year == cat.year
                        and tr.tr_type == "expense"
                        and tr.secondary == cat.secondary
                    ):
                        tr_list.append(tr)

            tr_get = uow.transaction.get(id_user, None, None, tr_type="expense")
            compare_tr(tr_list, tr_get)

            # ----------------------
            # ----------------------
            # --- by user, primary
            tr_list = []
            cat_prim_list = uow.category.get_primary_list(id_user, None, None)
            cat = random.choice(cat_prim_list)
            for tr in tr_tot_list:
                if tr.primary == cat.primary and tr.tr_type == cat.category_type:
                    tr_list.append(tr)

            tr_get = uow.transaction.get(
                id_user,
                None,
                None,
                tr_type=cat.category_type,
                primary=cat.primary,
            )
            compare_tr(tr_list, tr_get)

            # ----------------------
            # ----------------------
            # --- by user, secondary
            tr_list = []
            cat_sec_list = uow.category.get_secondary_list(id_user, None, None)
            cat = random.choice(cat_sec_list)
            for tr in tr_tot_list:
                if (
                    tr.primary == cat.primary
                    and tr.tr_type == "expense"
                    and tr.secondary == cat.secondary
                ):
                    tr_list.append(tr)

            tr_get = uow.transaction.get(
                id_user,
                None,
                None,
                tr_type=cat.category_type,
                primary=cat.primary,
                secondary=cat.secondary,
            )
            compare_tr(tr_list, tr_get)


def test_get_summary(db_env) -> None:
    currencies = UtilTest.currencies

    db_path = db_env

    with UnitOfWork(db_path) as uow:
        UtilTest.init_database(uow)
        user_list, cat_list, tr_tot_list = UtilTest.fill_user_cat_tr(uow, n_tr=1000)
        _ = UtilTest.add_exchange_rate(uow, tr_tot_list)

        n = 5

        for _ in range(n):
            id_user = random.choice(tr_tot_list).id_user

            for tr_type in ("expense", "income"):
                compare(
                    uow,
                    currencies,
                    id_user,
                    tr_type=tr_type,
                    begin_date=None,
                    end_date=None,
                    primary=None,
                    secondary=None,
                )

                begin_date = UtilTest.generate_random_date()

                compare(
                    uow,
                    currencies,
                    id_user,
                    tr_type=tr_type,
                    begin_date=begin_date,
                    end_date=None,
                    primary=None,
                    secondary=None,
                )

                end_date = UtilTest.generate_random_date()
                while end_date <= begin_date:
                    end_date = UtilTest.generate_random_date()

                compare(
                    uow,
                    currencies,
                    id_user,
                    tr_type=tr_type,
                    begin_date=begin_date,
                    end_date=end_date,
                    primary=None,
                    secondary=None,
                )

                cat_prim_list = uow.category.get_primary_list(id_user, None, tr_type)
                cat_prim = random.choice(cat_prim_list)

                compare(
                    uow,
                    currencies,
                    id_user,
                    tr_type=tr_type,
                    begin_date=None,
                    end_date=None,
                    primary=cat_prim.primary,
                    secondary=None,
                )

                cat_sec_list = uow.category.get_secondary_list(id_user, None, None)
                cat_sec = random.choice(cat_sec_list)

                compare(
                    uow,
                    currencies,
                    id_user,
                    tr_type=tr_type,
                    begin_date=None,
                    end_date=None,
                    primary=cat_sec.primary,
                    secondary=cat_sec.secondary,
                )

    # Creating a new connection will create a new database only if using db_path =
    # :memory: If using the temp_path the code below may have some problems

    # If some exchange rate are not present in the database an exception is raised.
    with UnitOfWork(db_path) as uow:
        UtilTest.init_database(uow)
        user_list, cat_list, tr_tot_list = UtilTest.fill_user_cat_tr(uow, n_tr=500)
        n_exc = len(tr_tot_list) - 10
        _ = UtilTest.add_exchange_rate(uow, random.choices(tr_tot_list, k=n_exc))

        id_user = random.choice(tr_tot_list).id_user
        to_currency = random.choice(currencies)
        try:
            _, is_valid = uow.transaction.get_summary(id_user, None, None, "expense", to_currency)

            assert not is_valid  # == False
        except EntityNotFoundError:
            # If the smallest date is removed an error is raised since the exchange rate
            # for that rate doesn't exist (and also for past dates).
            assert True


def test_get_by_id_cat(db_env) -> None:
    def compare_tr(tr_list, tr_get):
        tr_list = sorted(tr_list, key=transaction_sort_key)
        tr_get = sorted(tr_get, key=transaction_sort_key)
        assert tr_list == tr_get

    db_path = db_env

    with UnitOfWork(db_path) as uow:
        UtilTest.init_database(uow)
        _, cat_list, tr_tot_list = UtilTest.fill_user_cat_tr(uow, n_prim=5, n_tr=500)
        n = 25

        for _ in range(n):
            cat = random.choice(cat_list)
            cat_list = uow.category.get_secondary_list(cat.id_user, None, None)
            cat = random.choice(cat_list)

            begin_date = date(cat.year - 1, 1, 1)
            end_date = date(cat.year + 1, 1, 1)
            tr_list = uow.transaction.get(
                id_user=cat.id_user,
                begin_date=begin_date,
                end_date=end_date,
                tr_type=cat.category_type,
                primary=cat.primary,
                secondary=cat.secondary,
            )

            tr_list = [tr for tr in tr_list if tr.tr_date.year == cat.year]

            tr_get = uow.transaction.get_by_id_cat(cat.id_secondary)
            compare_tr(tr_list, tr_get)


def test_edit_transaction(db_env):
    db_path = db_env

    with UnitOfWork(db_path) as uow:
        UtilTest.init_database(uow)
        _, _, tr_list = UtilTest.fill_user_cat_tr(uow, n_tr=1000)
        n = 15

        for _ in range(n):
            tr_e = random.choice(tr_list)
            tr_list = uow.transaction.get(tr_e.id_user, None, None)
            tr_e = random.choice(tr_list)

            tr_e.value = random.random() * 10000
            tr_e.tr_date = tr_e.tr_date.replace(month=2, day=6)
            tr_e.description = UtilTest.generate_random_string()
            tr_e.name = UtilTest.generate_random_string()

            tr_e_in = TransactionIn(
                id_user=tr_e.id_user,
                primary=tr_e.primary,
                secondary=tr_e.secondary,
                tr_type=tr_e.tr_type,
                tr_date=tr_e.tr_date,
                name=tr_e.name,
                value=tr_e.value,
                currency=tr_e.currency,
                description=tr_e.description,
            )

            uow.transaction.edit(tr_e.id, tr_e_in)

            tr_list = uow.transaction.get(tr_e.id_user, None, None)
            for tr in tr_list:
                if tr.id == tr_e.id:
                    assert tr_e == tr
                    break


def test_delete_transaction(db_env):
    db_path = db_env

    with UnitOfWork(db_path) as uow:
        UtilTest.init_database(uow)
        _, _, tr_list = UtilTest.fill_user_cat_tr(uow, n_tr=1000)
        tr1 = random.choice(tr_list)

        n = 5
        for _ in range(n):
            tr_list = uow.transaction.get(tr1.id_user, None, None)
            tr_d = random.choice(tr_list)

            uow.transaction.delete(tr_d.id)

            tr_list = uow.transaction.get(tr1.id, None, None)

            for tr in tr_list:
                if tr.id == tr_d.id:
                    raise AssertionError("The transaction has not been deleted")


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


def compare(
    uow: UnitOfWork,
    currencies,
    id_user,
    tr_type,
    begin_date,
    end_date,
    primary,
    secondary,
):
    tr_list = uow.transaction.get(
        id_user,
        begin_date,
        end_date,
        tr_type,
        primary,
        secondary,
    )
    # print(tr_list)

    for to_currency in currencies:
        summary = {}
        is_valid = True
        for tr in tr_list:
            if tr.primary not in summary.keys():
                summary[tr.primary] = {}

            tr_secondary = tr.secondary if tr.secondary is not None else "N/A"

            if tr_secondary not in summary[tr.primary].keys():
                summary[tr.primary][tr_secondary] = {}

            tr_date = f"{tr.tr_date.strftime('%Y-%m')}"

            if tr_date not in summary[tr.primary][tr_secondary].keys():
                summary[tr.primary][tr_secondary][tr_date] = 0

            # convert the value with the given exchange rates
            if tr.currency == to_currency:
                value = tr.value
            else:
                exc_to = uow.exchange_rate.get(tr.tr_date, to_currency=to_currency)

                if exc_to:  # not an empty list
                    exc_to = exc_to[0]

                    if tr.currency == exc_to.from_currency:
                        value = tr.value * exc_to.rate

                        if not exc_to.is_updated:
                            is_valid = False

                    else:
                        exc_from = uow.exchange_rate.get(tr.tr_date, to_currency=tr.currency)[0]

                        value = tr.value / exc_from.rate * exc_to.rate

                        if not exc_to.is_updated or not exc_from.is_updated:
                            is_valid = False

                # ie to_currency = exc.from_currency
                else:
                    exc_to = uow.exchange_rate.get(tr.tr_date, to_currency=tr.currency)[0]

                    value = tr.value / exc_to.rate

                    if not exc_to.is_updated:
                        is_valid = False

            summary[tr.primary][tr_secondary][tr_date] += value

        summ_get, is_valid_get = uow.transaction.get_summary(
            id_user,
            begin_date,
            end_date,
            tr_type,
            to_currency,
            primary,
            secondary,
        )

        summary = sort_nested_dict(summary)
        summ_get = sort_nested_dict(summ_get)

        for prim in summary.keys():
            for sec in summary[prim].keys():
                for month, value in summary[prim][sec].items():
                    summary[prim][sec][month] = round(value, 5)

        for prim in summ_get.keys():
            for sec in summ_get[prim].keys():
                for month, value in summ_get[prim][sec].items():
                    summ_get[prim][sec][month] = round(value, 5)

        assert summary == summ_get
        assert is_valid == is_valid_get


def sort_nested_dict(d):
    """Sorts a nested dictionary by its keys at every level."""
    return {
        primary_key: {
            secondary_key: dict(sorted(month_year_dict.items()))
            for secondary_key, month_year_dict in sorted(secondary_dict.items())
        }
        for primary_key, secondary_dict in sorted(d.items())
    }
