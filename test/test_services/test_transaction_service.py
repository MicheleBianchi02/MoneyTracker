import calendar
import random
from datetime import date, timedelta

from src.core.domain.category import CategoryIn
from src.core.domain.exchange_rate import ExchangeRate
from src.core.domain.transaction import TransactionIn
from src.core.services.startup import EXC_DATE_CONFIG_NAME
from src.core.services.transaction_service import TransactionServices
from src.infrastructure.exchange_rate_provider.exchange_rate import ExchangeRateProvider
from src.infrastructure.fake_repo.fake_unit_of_work import FakeUnitOfWork
from test.util_test import UtilTest


def test_add_transaction():
    """In this test we just need to see if the exchange rates are added correctly.
    Because adding the transaction will simply call uow.transactions.add that has
    already been tested in repositories's test"""

    tr_service = TransactionServices()
    uow = FakeUnitOfWork()

    starting_date = "2025-01-01"
    maximum_date = "2025-05-31"

    tr_date_list = []

    tr_date_list.append(date(2025, 1, 1))
    tr_date_list.append(date(2025, 1, 2))
    tr_date_list.append(date(2025, 1, 3))
    tr_date_list.append(date(2025, 2, 8))
    tr_date_list.append(date(2025, 4, 19))

    # in future
    tr_date_list.append(date(2025, 6, 1))
    tr_date_list.append(date(2025, 6, 2))
    tr_date_list.append(date(2025, 6, 3))
    tr_date_list.append(date(2025, 8, 8))
    tr_date_list.append(date(2026, 1, 1))

    # far past
    tr_date_list.append(date(2020, 1, 1))
    tr_date_list.append(date(2020, 1, 2))
    tr_date_list.append(date(2020, 1, 3))
    tr_date_list.append(date(2023, 8, 8))
    tr_date_list.append(date(2024, 12, 31))

    with uow:
        id_user = uow.user.add(UtilTest.generate_random_string(), UtilTest.generate_random_string())

        uow.app_config.add(EXC_DATE_CONFIG_NAME, starting_date)

        exc_provider = ExchangeRateProvider()

        from_curr = exc_provider.base_currency
        available_currencies = exc_provider.available_currencies

        exc_list = []

        exc_date = date.fromisoformat(starting_date)
        end_date = date.fromisoformat(maximum_date)
        while exc_date <= end_date:
            for curr in available_currencies:
                if curr != from_curr:
                    exc = ExchangeRate(
                        from_currency=from_curr,
                        to_currency=curr,
                        rate=random.random() * 3,
                        rate_date=exc_date,
                        is_updated=True,
                    )

                    exc_list.append(exc)

            exc_date += timedelta(days=1)

        uow.exchange_rate.add(exc_list)

    # Add category to the database. We use only one primary with no secondaries since
    # the porpouse of this test is not to control the repository.

    primary = UtilTest.generate_random_string()
    secondary = None

    tr_year_set = set()
    tr_list = []
    for tr_date in tr_date_list:
        tr_list.append(
            TransactionIn(
                id_user=id_user,
                primary=primary,
                secondary=secondary,
                tr_type="expense",
                tr_date=tr_date,
                name=UtilTest.generate_random_string(),
                value=random.random() * 10000,
                currency=random.choice(available_currencies),
                description=UtilTest.generate_random_string(),
            )
        )

        tr_year_set.add(tr_date.year)

    cat_list = []
    for tr_year in tr_year_set:
        cat_list.append(
            CategoryIn(
                id_user=id_user,
                year=tr_year,
                category_type="expense",
                primary=primary,
                secondary=secondary,
            )
        )

    with uow:
        uow.category.add(cat_list)

    tr_service.add_transaction(uow, tr_list)

    month_year = set()
    for tr_date in tr_date_list:
        year = tr_date.year
        month = tr_date.month
        last_day = calendar.monthrange(year, month)[1]
        month_year = [date(year, month, day) for day in range(1, last_day + 1)]

    with uow:
        for exc_date in month_year:
            exc_get = uow.exchange_rate.get(exc_date)
            assert len(exc_get) == len(available_currencies) - 1

            # Dates that will never be updated above those dates since they were not
            # in use from those dates till now
            for exc in exc_get:
                if exc.to_currency == "LVL":
                    if exc.rate_date > date(2014, 2, 1):
                        assert not exc.is_updated

                if exc.to_currency == "LTL":
                    if exc.rate_date > date(2013, 2, 1):
                        assert not exc.is_updated

                if exc.to_currency == "HRK":
                    if exc.rate_date > date(2023, 2, 1):
                        assert not exc.is_updated

                if exc.to_currency == exc.from_currency:
                    raise AssertionError("Same currency for from_currency and to_currency")
