import random
import sqlite3
from datetime import date

import pytest
from test.util_test import UtilTest

from moneytracker.core.domain.transaction import TransactionOut, TransactionRepoIn
from moneytracker.core.exceptions import EntityNotFoundError
from moneytracker.infrastructure.connection_pool import ConnectionPool
from moneytracker.infrastructure.sqlite.repositories.transaction_repository import NONE_REPLACEMENT
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


def test_add_transaction(connection: str) -> None:
    currencies = UtilTest.currencies

    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        _, cat_list = UtilTest.fill_user_cat(uow)
        cat1 = random.choice(cat_list)

        # --- add income
        cat_list = uow.category.get_primary_list(cat1.id_user, None, "income")
        cat1 = random.choice(cat_list)
        id_user = cat1.id_user

        tr_date = UtilTest.generate_random_date(cat1.year)

        tr = TransactionRepoIn(
            id_user=id_user,
            id_cat=cat1.id_primary,
            tr_date=tr_date,
            name=UtilTest.generate_random_string(),
            value=random.random() * 10000,
            currency=random.choice(currencies),
            description=UtilTest.generate_random_string(),
        )

        uow.transaction.add([tr])

        # --- add primary expense

        cat_list = uow.category.get_primary_list(id_user, None, "expense")
        cat1 = random.choice(cat_list)
        tr_date = UtilTest.generate_random_date(cat1.year)

        tr = TransactionRepoIn(
            id_user=id_user,
            id_cat=cat1.id_primary,
            tr_date=tr_date,
            name=UtilTest.generate_random_string(),
            value=random.random() * 10000,
            currency=random.choice(currencies),
            description=UtilTest.generate_random_string(),
        )

        uow.transaction.add([tr])

        # --- add secondary expense
        cat_list = uow.category.get_secondary_list(id_user, None, None)
        cat1 = random.choice(cat_list)

        tr_date = UtilTest.generate_random_date(cat1.year)

        tr = TransactionRepoIn(
            id_user=id_user,
            id_cat=cat1.id_secondary,
            tr_date=tr_date,
            name=UtilTest.generate_random_string(),
            value=random.random() * 10000,
            currency=random.choice(currencies),
            description=UtilTest.generate_random_string(),
        )

        uow.transaction.add([tr])

        # check foreign key
        id_user = 20341232
        tr.id_user = id_user
        try:
            uow.transaction.add([tr])
            error = True

        except Exception:
            error = False

        if error:
            raise AssertionError("""No error is raised when adding transaction with 
            id user not present in the database. foreign_key may be disabled""")


def test_get_transaction(connection):
    def compare_tr(tr_list, tr_get):
        for tr in tr_list:
            tr.id = 0
        for tr in tr_get:
            tr.id = 0

        tr_list = sorted(tr_list, key=transaction_sort_key)
        tr_get = sorted(tr_get, key=transaction_sort_key)
        assert tr_list == tr_get

    n_tr = 100

    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        _, cat_list, tr_tot_list = UtilTest.fill_user_cat_tr(uow, n_tr=n_tr)
        n = 25
        # not just one becouse for some test i need to check on both income and expense

        for _ in range(n):
            tr1 = random.choice(tr_tot_list)
            id_user = tr1.id_user
            tr_date = tr1.tr_date

            # -----------
            # --- by user
            tr_list = [tr for tr in tr_tot_list if tr.id_user == id_user]
            tr_get, is_valid = uow.transaction.get(id_user, None, None)
            compare_tr(tr_list, tr_get)

            # --- by user, begin_date
            tr_list = [tr for tr in tr_tot_list if tr.id_user == id_user and tr.tr_date >= tr_date]
            tr_get, is_valid = uow.transaction.get(id_user, tr_date, None)
            compare_tr(tr_list, tr_get)

            # --- by user, end_date
            tr_list = [tr for tr in tr_tot_list if tr.id_user == id_user and tr.tr_date <= tr_date]
            tr_get, is_valid = uow.transaction.get(id_user, None, tr_date)
            compare_tr(tr_list, tr_get)

            # --- by user, begin_date, end_date (2 year interval)
            begin_date = tr_date.replace(year=tr_date.year - 1, month=1, day=1)
            end_date = tr_date.replace(year=tr_date.year + 1, month=1, day=1)

            tr_list = [
                tr
                for tr in tr_tot_list
                if tr.id_user == id_user and tr.tr_date >= begin_date and tr.tr_date <= end_date
            ]
            tr_get, is_valid = uow.transaction.get(id_user, begin_date, end_date)
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

            tr_get, is_valid = uow.transaction.get(id_user, None, None, tr_type="income")
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

            tr_get, is_valid = uow.transaction.get(id_user, None, None, tr_type="expense")
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

            tr_get, is_valid = uow.transaction.get(
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

            tr_get, is_valid = uow.transaction.get(
                id_user,
                None,
                None,
                tr_type=cat.category_type,
                primary=cat.primary,
                secondary=cat.secondary,
            )
            compare_tr(tr_list, tr_get)

            # --- order
            tr_list = [tr for tr in tr_tot_list if tr.id_user == id_user]
            order_value = ["name", "date", "value", "currency", "primary", "secondary"]
            order_dir = ["ASC", "DESC"]

            for order in order_value:
                for dir in order_dir:
                    tr_list_get, _ = uow.transaction.get(
                        id_user, None, None, order=order, order_dir=dir
                    )

                    if order == "name":
                        order_list = [tr.name for tr in tr_list]
                        order_list_get = [tr.name for tr in tr_list_get]

                    elif order == "date":
                        order_list = [tr.tr_date for tr in tr_list]
                        order_list_get = [tr.tr_date for tr in tr_list_get]

                    elif order == "value":
                        order_list = [tr.value for tr in tr_list]
                        order_list_get = [tr.value for tr in tr_list_get]

                    elif order == "currency":
                        order_list = [(tr.currency, tr.tr_date) for tr in tr_list]
                        order_list_get = [(tr.currency, tr.tr_date) for tr in tr_list_get]

                    elif order == "primary":
                        order_list = [(tr.primary, tr.secondary) for tr in tr_list]
                        order_list_get = [(tr.primary, tr.secondary) for tr in tr_list_get]

                    elif order == "secondary":
                        # secondary can be None
                        # NULL values are returned as first element by the database
                        order_list = []
                        for tr in tr_list:
                            secondary = (
                                tr.secondary
                                if tr.secondary is not None
                                else "0000000000000000000000"
                            )
                            order_list.append((secondary, tr.primary))

                        order_list_get = []
                        for tr in tr_list_get:
                            secondary = (
                                tr.secondary
                                if tr.secondary is not None
                                else "0000000000000000000000"
                            )
                            order_list_get.append((secondary, tr.primary))

                    if dir == "DESC":
                        order_list.sort(reverse=True)
                    else:
                        order_list.sort()

                    assert order_list == order_list_get

            # --- limit and offset
            tr_list = [tr for tr in tr_tot_list if tr.id_user == id_user]
            limit = random.randint(0, len(tr_list))

            tr_list_get, _ = uow.transaction.get(id_user, None, None, limit=limit)
            assert len(tr_list_get) == limit

            if limit > 0:
                offset = random.randint(0, limit)

                tr_list.sort(key=lambda tr: tr.name)

                tr_list_offset = tr_list[offset : limit + offset]
                tr_list_get, _ = uow.transaction.get(
                    id_user, None, None, limit=limit, offset=offset, order="name"
                )

                compare_tr(tr_list_offset, tr_list_get)

        # --- to_currency
        _ = UtilTest.add_exchange_rate(uow, tr_tot_list)

        to_currency = random.choice(UtilTest.currencies)

        is_valid = True
        tr_list = []
        for tr in tr_tot_list:
            if tr.id_user == id_user:
                tr_1 = tr.model_copy()
                tr_1.value, is_tr_valid = convert_value(uow, to_currency, tr_1)
                tr_1.currency = to_currency
                tr_list.append(tr_1)

                if not is_tr_valid and is_valid:
                    is_valid = False

        tr_get, is_valid_get = uow.transaction.get(id_user, None, None, to_currency)
        compare_tr(tr_list, tr_get)
        assert is_valid == is_valid_get

        # --- with everything

        for _ in range(n * 3):
            tr = random.choice(tr_tot_list)
            if random.random() < 0.5:
                primary = None
            else:
                primary = tr.primary

                if random.random() < 0.5:
                    secondary = None
                else:
                    secondary = tr.secondary

            id_user = tr.id_user
            begin_date = date(2002, 1, 1)
            end_date = date(2022, 12, 31)
            to_currency = random.choice(UtilTest.currencies)
            tr_type = tr.tr_type
            secondary = None
            order = "name"
            order_dir = random.choice(["ASC", "DESC"])
            limit = 20
            offset = 2
            name_similarity = ""

            tr_list_get, _ = uow.transaction.get(
                id_user=id_user,
                begin_date=begin_date,
                end_date=end_date,
                to_currency=to_currency,
                tr_type=tr_type,
                primary=primary,
                secondary=secondary,
                order=order,
                order_dir=order_dir,
                limit=limit,
                offset=offset,
                name=name_similarity,
            )

            tr_list = []
            for tr in tr_tot_list:
                tr = tr.model_copy()

                if tr.tr_date >= begin_date and tr.tr_date <= end_date:
                    if tr.tr_type == tr_type and tr.id_user == id_user:
                        if primary is None or tr.primary == primary:
                            tr_list.append(tr)

                            tr.value, _ = convert_value(uow, to_currency, tr)
                            tr.currency = to_currency

            reverse = True if order_dir == "DESC" else False
            if order == "name":
                tr_list = sorted(tr_list, reverse=reverse, key=lambda tr: tr.name)

            tr_list = tr_list[offset : limit + offset]

            compare_tr(tr_list, tr_list_get)

        # --- name similarity
        # Must be at the end since we are adding transactions

        cat = random.choice(cat_list)

        name_list = ["%asdas%sda_da", "asd%\\__\\%%%asda%%, %a%a_a____", "__", "\\_%asd%_\\"]

        for name in name_list:
            tr = TransactionRepoIn(
                id_user=id_user,
                id_cat=cat.id_primary,
                tr_date=UtilTest.generate_random_date(cat.year),
                name=name,
                value=random.random() * 1000,
                currency=random.choice(UtilTest.currencies),
                description=UtilTest.generate_random_string(),
            )

            uow.transaction.add([tr])

        tr_list, _ = uow.transaction.get(id_user, None, None)

        name_to_test = [
            "a",
            "asd%",
            "\\",
            "\\\\\\_",
            "%asdas%",
            "_",
        ]

        for name_sim in name_to_test:
            name_sim_len = len(name_sim)

            tr_sim_list = [
                tr.model_copy()
                for tr in tr_list
                if tr.name[:name_sim_len].upper() == name_sim.upper()
            ]

            for tr in tr_sim_list:
                tr.name = tr.name.upper()

            tr_list_get, _ = uow.transaction.get(id_user, None, None, name=name_sim)
            tr_list_get = [tr.model_copy() for tr in tr_list_get]
            for tr in tr_list_get:
                tr.name = tr.name.upper()

            compare_tr(tr_sim_list, tr_list_get)


def test_get_summary(connection) -> None:
    currencies = UtilTest.currencies

    with UnitOfWork(connection) as uow:
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


def test_convert_exception(connection):
    # If some exchange rate are not present in the database an exception is raised.
    currencies = UtilTest.currencies
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        user_list, cat_list, tr_tot_list = UtilTest.fill_user_cat_tr(uow, n_tr=500)
        n_exc = len(tr_tot_list) - 10
        _ = UtilTest.add_exchange_rate(uow, random.choices(tr_tot_list, k=n_exc))

        id_user = random.choice(tr_tot_list).id_user
        to_currency = random.choice(currencies)
        try:
            _, is_valid = uow.transaction.get_summary(id_user, None, None, "expense", to_currency)
            assert not is_valid  # == False

            _, is_valid = uow.transaction.get(id_user, None, None, to_currency)
            assert not is_valid

        except EntityNotFoundError:
            # If the smallest date is removed an error is raised since the exchange rate
            # for that rate doesn't exist (and also for past dates).
            assert True


def test_get_by_id_cat(connection) -> None:
    def compare_tr(tr_list, tr_get):
        tr_list = sorted(tr_list, key=transaction_sort_key)
        tr_get = sorted(tr_get, key=transaction_sort_key)
        assert tr_list == tr_get

    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        user_list, cat_list_tot, tr_tot_list = UtilTest.fill_user_cat_tr(uow, n_prim=15, n_tr=500)
        n = 25

        for _ in range(n):
            id_user = random.choice(user_list).id
            cat_list = uow.category.get_secondary_list(id_user, None, None)
            if cat_list:
                cat = random.choice(cat_list)

                begin_date = date(cat.year - 1, 1, 1)
                end_date = date(cat.year + 1, 1, 1)
                tr_list, _ = uow.transaction.get(
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


def test_edit_transaction(connection):
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        _, _, tr_list = UtilTest.fill_user_cat_tr(uow, n_tr=1000)
        n = 15

        for _ in range(n):
            tr_e = random.choice(tr_list)
            id_user = tr_e.id_user
            tr_list, _ = uow.transaction.get(tr_e.id_user, None, None)
            tr_e = random.choice(tr_list)

            new_cat_list = uow.category.get(id_user, None, tr_e.tr_type)
            new_cat = random.choice(new_cat_list)
            if new_cat.id_secondary is None:
                id_cat = new_cat.id_primary
            else:
                id_cat = new_cat.id_secondary

            new_date = UtilTest.generate_random_date(new_cat.year)

            tr_e.value = random.random() * 10000
            tr_e.tr_date = new_date
            tr_e.currency = random.choice(UtilTest.currencies)
            tr_e.description = UtilTest.generate_random_string()
            tr_e.name = UtilTest.generate_random_string()

            tr_e.primary = new_cat.primary
            tr_e.secondary = new_cat.secondary

            tr_e_in = TransactionRepoIn(
                id_user=tr_e.id_user,
                id_cat=id_cat,
                tr_date=tr_e.tr_date,
                name=tr_e.name,
                value=tr_e.value,
                currency=tr_e.currency,
                description=tr_e.description,
            )

            uow.transaction.edit(tr_e.id, tr_e_in)

            tr_list, _ = uow.transaction.get(tr_e.id_user, None, None)
            for tr in tr_list:
                if tr.id == tr_e.id:
                    assert tr_e == tr
                    break


def test_delete_transaction(connection):
    with UnitOfWork(connection) as uow:
        UtilTest.init_database(uow)
        _, _, tr_list = UtilTest.fill_user_cat_tr(uow, n_tr=200)
        tr1 = random.choice(tr_list)

        n = 5
        for _ in range(n):
            tr_list, _ = uow.transaction.get(tr1.id_user, None, None)
            tr_d = random.choice(tr_list)

            uow.transaction.delete(tr_d.id)

            tr_list, _ = uow.transaction.get(tr1.id, None, None)

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


def convert_value(uow: UnitOfWork, to_currency: str, tr: TransactionOut) -> tuple[float, bool]:
    # convert the value with the given exchange rates
    is_valid = True
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

    return value, is_valid


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
    tr_list, _ = uow.transaction.get(
        id_user,
        begin_date,
        end_date,
        tr_type=tr_type,
        primary=primary,
        secondary=secondary,
    )

    for to_currency in currencies:
        summary = {}
        is_valid = True
        for tr in tr_list:
            if tr.primary not in summary.keys():
                summary[tr.primary] = {}

            tr_secondary = tr.secondary if tr.secondary is not None else NONE_REPLACEMENT

            if tr_secondary not in summary[tr.primary].keys():
                summary[tr.primary][tr_secondary] = {}

            tr_date = f"{tr.tr_date.strftime('%Y-%m')}"

            if tr_date not in summary[tr.primary][tr_secondary].keys():
                summary[tr.primary][tr_secondary][tr_date] = 0

            value, is_tr_valid = convert_value(uow, to_currency, tr)

            if not is_tr_valid and is_valid:
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
        # is_valid can be false if is_updated is False


def sort_nested_dict(d):
    """Sorts a nested dictionary by its keys at every level."""
    return {
        primary_key: {
            secondary_key: dict(sorted(month_year_dict.items()))
            for secondary_key, month_year_dict in sorted(secondary_dict.items())
        }
        for primary_key, secondary_dict in sorted(d.items())
    }
