from datetime import date, timedelta

from src.core.services.startup import EXC_DATE_CONFIG_NAME, _add_exchange_rate
from src.infrastructure.exchange_rate_provider.exchange_rate import ExchangeRateProvider
from src.infrastructure.fake_repo.fake_unit_of_work import FakeUnitOfWork
from test.util_test import UtilTest

# TODO: Test what happen when there is no internet connection


def test_startup_from_empty():
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


def test_startup_from_filled():
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
