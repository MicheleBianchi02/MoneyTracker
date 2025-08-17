import calendar
import random
import string
from datetime import date

from src.core.domain.category import CategoryIn, CategoryOut
from src.core.domain.exchange_rate import ExchangeRate
from src.core.domain.setting import Setting
from src.core.domain.transaction import TransactionIn, TransactionOut
from src.core.domain.user import User
from src.infrastructure.exchange_rate_provider.exchange_rate import ExchangeRateProvider
from src.infrastructure.sqlite.initializer import initialize_database
from src.infrastructure.sqlite.unit_of_work import UnitOfWork


class UtilTest:
    # currencies = ["USD", "EUR", "CAD", "GBP", "NZD", "CNY"]
    currencies = ExchangeRateProvider().available_currencies

    @staticmethod
    def generate_random_string():
        len = random.randint(10, 20)

        char_set = string.ascii_uppercase + string.digits
        return "".join(random.sample(char_set * len, len))

    @staticmethod
    def generate_random_date(year: int | None = None) -> date:
        """Generate random date with the given year. If year is None generate
        a random year"""
        if year is None:
            year = random.randint(2000, 2024)
        month = random.randint(1, 12)
        day = random.randint(1, 31)

        _, days_in_month = calendar.monthrange(year, month)

        if day > days_in_month:
            day = days_in_month

        return date(year, month, day)

    @staticmethod
    def init_database(uow: UnitOfWork) -> None:
        """Used only to initialize the database.

        Needed such that only one connection per test is created. Usefull when using
        in memory database (db_path = :memory:)."""

        initialize_database(uow.connection)

    @staticmethod
    def fill_user(uow: UnitOfWork, n_user: int = 3) -> list[User]:
        """Add random user to the database and return the User list with the
        correct ids"""

        user_list = []
        for _ in range(n_user):
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

            user_list.append(
                User(
                    username=username,
                    password=UtilTest.generate_random_string(),
                )
            )

        for user in user_list:
            id_user = uow.user.add(user.username, user.password)
            user.id = id_user

        return user_list

    @staticmethod
    def fill_user_cat(
        uow: UnitOfWork,
        n_user=3,
        n_prim=300,
        n_sec=10,
    ) -> tuple[list[User], list[CategoryOut]]:
        """Add n_user users, n_prim primary categories and n_sec secondary categories
        to each primary to the database.
        The list of users, and category are returned.
        Each returned category has the wrong value of id_primary (the one in the db)
        id_secondary (None only for income).
        """

        # n_prim should not be too small (150 can be problemantic) since it can occour
        # that no secondaries are created.

        user_list = UtilTest.fill_user(uow, n_user)

        # increase the number of expenses in the db
        possible_cat_type = ["income", "expense", "expense"]

        cat_list_in = []
        cat_list_out = []

        # Add a secondary category that has the same name as a primary (not the parent one)

        id_user = random.choice(user_list).id
        year = UtilTest.generate_random_date().year
        primary_1 = UtilTest.generate_random_string()
        cat_list_in.append(
            CategoryIn(
                id_user=id_user,
                year=year,
                category_type="expense",
                primary=primary_1,
                secondary=None,
            )
        )

        cat_list_out.append(
            CategoryOut(
                id_primary=0,
                id_secondary=0,
                id_user=id_user,
                year=year,
                category_type="expense",
                primary=primary_1,
                secondary=None,
            )
        )

        primary_2 = UtilTest.generate_random_string()
        cat_list_in.append(
            CategoryIn(
                id_user=id_user,
                year=year,
                category_type="expense",
                primary=primary_2,
                secondary=primary_1,
            )
        )

        cat_list_out.append(
            CategoryOut(
                id_primary=0,
                id_secondary=0,
                id_user=id_user,
                year=year,
                category_type="expense",
                primary=primary_2,
                secondary=primary_1,
            )
        )

        n_prim_rep = int(n_prim / 2)

        for _ in range(n_prim - n_prim_rep - 2):
            year = UtilTest.generate_random_date().year
            user = random.choice(user_list)
            id_user = user.id

            cat_type = random.choice(possible_cat_type)

            if cat_type == "income":
                primary = UtilTest.generate_random_string()
                cat = CategoryIn(
                    id_user=id_user,
                    year=year,
                    category_type="income",
                    primary=primary,
                    secondary=None,
                )

                cat_list_in.append(cat)

                cat_out = CategoryOut(
                    id_primary=0,
                    id_secondary=None,
                    id_user=id_user,
                    year=year,
                    category_type="income",
                    primary=primary,
                    secondary=None,
                )

                cat_list_out.append(cat_out)

            else:
                primary = UtilTest.generate_random_string()

                # Half of the expenses categories are only primary, they don't have any
                # secondary

                if random.random() < 0.5:
                    cat = CategoryIn(
                        id_user=id_user,
                        year=year,
                        category_type="expense",
                        primary=primary,
                        secondary=None,
                    )

                    cat_list_in.append(cat)

                    cat_out = CategoryOut(
                        id_primary=0,
                        id_secondary=0,
                        id_user=id_user,
                        year=year,
                        category_type="expense",
                        primary=primary,
                        secondary=None,
                    )

                    cat_list_out.append(cat_out)

                else:
                    for _ in range(n_sec):
                        secondary = UtilTest.generate_random_string()
                        cat = CategoryIn(
                            id_user=id_user,
                            year=year,
                            category_type="expense",
                            primary=primary,
                            secondary=secondary,
                        )

                        cat_list_in.append(cat)

                        cat_out = CategoryOut(
                            id_primary=0,
                            id_secondary=0,
                            id_user=id_user,
                            year=year,
                            category_type="expense",
                            primary=primary,
                            secondary=secondary,
                        )

                        cat_list_out.append(cat_out)

        # Add categories to other year with the same name of already present categories.
        # We have to test if having the same category name in different year would create
        # problems.

        # In cat_list_in there are CategoryOut object. For income type they are
        # primary but for expenses they have both primary and secondary. Since the
        # number of secondary is n_prim, we need to add primaries up to n_prim.
        # To do so, for expenses, we add all the secondaries for each primary.
        # The two while are needed since in the cat_list_in are not present the
        # primary for expenses (ie secondary=None and category_type = expense)

        i = 0
        j = 0  # count n_primary added
        while j < n_prim_rep:
            cat1 = cat_list_in[i]

            if cat1.category_type == "income":
                catIn = CategoryIn(
                    id_user=cat1.id_user,
                    year=cat1.year + 1,
                    category_type=cat1.category_type,
                    primary=cat1.primary,
                    secondary=cat1.secondary,
                )
                catOut = CategoryOut(
                    id_primary=0,
                    id_secondary=None,
                    id_user=cat1.id_user,
                    year=cat1.year + 1,
                    category_type=cat1.category_type,
                    primary=cat1.primary,
                    secondary=cat1.secondary,
                )
                cat_list_in.append(catIn)
                cat_list_out.append(catOut)

                i += 1
                j += 1

            else:
                # add all secondaries for the given primary
                cat_sec = cat_list_in[i]
                primary = cat_sec.primary
                while cat_sec.category_type == "expense" and cat_sec.primary == primary:
                    catIn = CategoryIn(
                        id_user=cat_sec.id_user,
                        year=cat_sec.year + 1,
                        category_type=cat_sec.category_type,
                        primary=cat_sec.primary,
                        secondary=cat_sec.secondary,
                    )
                    catOut = CategoryOut(
                        id_primary=0,
                        id_secondary=0,
                        id_user=cat_sec.id_user,
                        year=cat_sec.year + 1,
                        category_type=cat_sec.category_type,
                        primary=cat_sec.primary,
                        secondary=cat_sec.secondary,
                    )
                    cat_list_in.append(catIn)
                    cat_list_out.append(catOut)
                    i += 1
                    cat_sec = cat_list_in[i]

                j += 1

        uow.category.add(cat_list_in)

        return user_list, cat_list_out

    @staticmethod
    def fill_user_cat_tr(
        uow: UnitOfWork,
        n_user: int = 3,
        n_prim: int = 300,
        n_sec: int = 10,
        n_tr: int = 500,
    ) -> tuple[list[User], list[CategoryOut], list[TransactionOut]]:
        """Add n_user users, n_prim primary categories, n_sec secondary categories
        and n_tr transactions to the database.
        The list of id_users, primary category and secondary categories and transactions
        are returned.
        The user list is the only with the correct ids.
        The order of returned element is:
        - user_list;
        - cat_list;
        - tr_list
        """

        currencies = UtilTest.currencies

        user_list, cat_list = UtilTest.fill_user_cat(
            uow,
            n_user=n_user,
            n_prim=n_prim,
            n_sec=n_sec,
        )

        tr_list_in = []
        tr_list_out = []
        for _ in range(n_tr):
            cat1 = random.choice(cat_list)
            cat_prim_list = uow.category.get_primary_list(cat1.id_user, None, None)
            cat_prim = random.choice(cat_prim_list)

            if cat_prim.category_type == "income":
                cat = cat_prim
            else:
                # expense
                cat_sec_list = uow.category.get_secondary_list(
                    cat_prim.id_user,
                    cat_prim.year,
                    cat_prim.primary,
                )

                # Some transactions have only primary
                if len(cat_sec_list) == 0:
                    cat = cat_prim

                else:
                    cat = random.choice(cat_sec_list)

            tr_date = UtilTest.generate_random_date(cat.year)
            name = UtilTest.generate_random_string()
            value = random.random() * 100000
            currency = random.choice(currencies)
            description = UtilTest.generate_random_string()
            tr_in = TransactionIn(
                id_user=cat.id_user,
                primary=cat.primary,
                secondary=cat.secondary,
                tr_type=cat.category_type,
                tr_date=tr_date,
                name=name,
                value=value,
                currency=currency,
                description=description,
            )

            tr_out = TransactionOut(
                id=0,
                id_user=cat.id_user,
                primary=cat.primary,
                secondary=cat.secondary,
                tr_type=cat.category_type,
                tr_date=tr_date,
                name=name,
                value=value,
                currency=currency,
                description=description,
            )

            tr_list_in.append(tr_in)
            tr_list_out.append(tr_out)

        uow.transaction.add(tr_list_in)

        return user_list, cat_list, tr_list_out

    @staticmethod
    def fill_user_setting(
        uow: UnitOfWork,
        settings: list[Setting],
        n_user: int = 3,
    ) -> tuple[list[User], dict[str, Setting]]:
        user_list = UtilTest.fill_user(uow, n_user)

        # It is required to create a copy of each setting since the one passed as an
        # argumenet to the function is actually a list of pointers. It means that
        # editing a setting inside this function will edit the list in the parent
        # script.
        setting_list = []
        for sett in settings:
            setting_list.append(sett.model_copy())

        ret_set_list = {}
        for user in user_list:
            user_set_list = []
            id_user = user.id

            for sett in setting_list:
                if sett.constrained:
                    all = random.choice(sett.allowed_settings)
                    value = all["item_value"]

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

                # need to be copied since they are pointer
                user_set_list.append(sett.model_copy())
                uow.user_setting.add(id_user, sett.name, value)

            ret_set_list[f"{id_user}"] = user_set_list
        return user_list, ret_set_list

    @staticmethod
    def add_exchange_rate(
        uow: UnitOfWork,
        tr_list: list[TransactionOut] | None,
        date_list: list[date] | None = None,
    ) -> list[ExchangeRate]:
        """Add exchange_rates with arbitrary values in the dates of the given
        transaction list. If transaction list is None, date_list must not be None.
        In this case, the exchange rates for the given list is added."""

        currencies = UtilTest.currencies

        if tr_list is not None:
            date_list = []
            for tr in tr_list:
                if tr.tr_date not in date_list:
                    date_list.append(tr.tr_date)

        exc_list = []
        for tr_date in date_list:
            # from currency must be the same for all exchange rate in the same date

            from_currency = random.choice(currencies)
            for currency in currencies:
                if currency != from_currency:
                    exc = ExchangeRate(
                        from_currency=from_currency,
                        to_currency=currency,
                        rate=random.random() * 3,
                        rate_date=tr_date,
                        is_updated=random.choice([True, False]),
                    )

                    exc_list.append(exc)

                    # This belowe slowe down the code a lot
                    # if exc not in exc_list:
                    #     exc_list.append(exc)

        uow.exchange_rate.add(exc_list)

        return exc_list
