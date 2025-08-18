from datetime import date, timedelta
from random import randint, random

from src.core.domain.exchange_rate import ExchangeRate
from src.core.exceptions import ExchangeRateApiError
from src.core.services.startup import (
    EXC_DATE_CONFIG_NAME,
    _add_exchange_rate,
    _update_exchange_rate,
)
from src.infrastructure.exchange_rate_provider.exchange_rate import ExchangeRateProvider
from src.infrastructure.fake_repo.fake_unit_of_work import FakeUnitOfWork
from test.util_test import UtilTest

# TODO: Test what happen when there is no internet connection


def test_startup_add_from_empty():
    """Test add exchange rate with empty database"""
    uow = FakeUnitOfWork()

    _add_exchange_rate(uow)

    with uow:
        max_date = ExchangeRateProvider().maximum_available_date
        st_date = uow.app_config.get(EXC_DATE_CONFIG_NAME)

        assert st_date is not None
        st_date = date.fromisoformat(st_date)

        year = date.today().year
        first_date = date(year, 1, 1)

        day_diff = (date.today() - first_date).days
        if day_diff <= 1:
            first_date = date(year - 1, 1, 1)

        assert first_date == st_date

        date_list = []
        exc_date = st_date
        while exc_date < max_date:
            date_list.append(exc_date)
            exc_date += timedelta(days=1)

        for exc_date in date_list:
            exc_get = uow.exchange_rate.get(exc_date)

            assert len(exc_get) == len(ExchangeRateProvider().available_currencies) - 1


def test_startup_add_from_filled():
    """Test adding exchange rate when already present in the database but not up to date."""
    uow = FakeUnitOfWork()

    with uow:
        max_date = date(2025, 8, 1)

        st_date = f"{max_date.year}-01-01"
        uow.app_config.add(EXC_DATE_CONFIG_NAME, st_date)
        st_date = date.fromisoformat(st_date)

        date_list = []
        exc_date = st_date
        while exc_date < max_date:
            date_list.append(exc_date)
            exc_date += timedelta(days=1)

        UtilTest.add_exchange_rate(uow, None, date_list)

    _add_exchange_rate(uow)

    pr_max_date = ExchangeRateProvider().maximum_available_date

    date_list = []
    exc_date = max_date
    while exc_date < pr_max_date:
        date_list.append(exc_date)
        exc_date += timedelta(days=1)

    with uow:
        for exc_date in date_list:
            exc_get = uow.exchange_rate.get(exc_date)

            assert len(exc_get) == len(ExchangeRateProvider().available_currencies) - 1


def test_update():
    uow = FakeUnitOfWork()
    exc_pr = ExchangeRateProvider()

    from_currency = exc_pr.base_currency
    available_currencies = exc_pr.available_currencies

    _add_exchange_rate(uow)

    with uow:
        # Must be smaller than the maximum date defined in _add_exchange_rate
        max_year = 2023

        n = 10

        date_list = []
        exc_list = []

        for _ in range(n):
            year = randint(2005, max_year)
            exc_date = UtilTest.generate_random_date(year)

            while exc_date in date_list:
                exc_date = UtilTest.generate_random_date(year)

            date_list.append(exc_date)

            for curr in available_currencies:
                if curr != from_currency:
                    exc = ExchangeRate(
                        from_currency=from_currency,
                        to_currency=curr,
                        rate=random() * 3,
                        rate_date=exc_date,
                        # is_updated=choice([True, False]),
                        is_updated=False,
                    )

                    exc_list.append(exc)

        uow.exchange_rate.add(exc_list)

    _update_exchange_rate(uow)

    exc_get = uow.exchange_rate.get_not_updated(None, None)

    curr_dict = {}
    for exc in exc_get:
        curr_dict.setdefault(exc.to_currency, [])
        curr_dict[exc.to_currency].append(exc.rate_date)

    for curr, date_list in curr_dict.items():
        try:
            exc_list, not_available_exc = exc_pr.get_exchange_rate(date_list, curr)
        except ExchangeRateApiError as e:
            assert "Empty Response.content" in str(e)
            # If at first try in _update_exchange_rate the rate were not available, it
            # means that requirind them will return an empty content
