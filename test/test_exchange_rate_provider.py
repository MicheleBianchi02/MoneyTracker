from datetime import date, timedelta

from src.core.domain.exchange_rate import ExchangeRate
from src.core.exceptions import ExchangeRateApiError
from src.infrastructure.exchange_rate_provider.exchange_rate import ExchangeRateProvider
from test.util_test import UtilTest


def test_get_exchange_rate_provider():
    currencies = UtilTest.currencies
    base_currency = ExchangeRateProvider().base_currency

    date_list = [date(2033, 1, 1), date(2044, 1, 1)]

    exc_list_get, exc_dict_get = ExchangeRateProvider().get_exchange_rate(date_list, base_currency)

    exc_dict = {}
    exc_dict["from_currency"] = base_currency

    assert exc_list_get == []
    assert exc_dict_get == exc_dict

    exc_list_get, exc_get = ExchangeRateProvider().get_exchange_rate(date_list, currencies)

    exc_dict = {}
    exc_dict["from_currency"] = base_currency
    for exc_date in date_list:
        key = exc_date.isoformat()

        exc_dict[key] = sorted(currencies)
        exc_dict[key].remove(base_currency)

    for key in exc_get.keys():
        if isinstance(exc_get[key], list):
            # otherwise the from_currency value will be transformed into a list
            exc_get[key] = sorted(exc_get[key])

    assert exc_list_get == []
    assert exc_dict == exc_get

    exc_list = [
        ExchangeRate(
            from_currency=base_currency,
            to_currency="USD",
            rate=1.0395,
            rate_date=date(2024, 12, 25),
            is_updated=True,
        ),
        ExchangeRate(
            from_currency=base_currency,
            to_currency="JPY",
            rate=163.25,
            rate_date=date(2024, 12, 25),
            is_updated=True,
        ),
        ExchangeRate(
            from_currency=base_currency,
            to_currency="USD",
            rate=1.0395,
            rate_date=date(2024, 12, 26),
            is_updated=True,
        ),
        ExchangeRate(
            from_currency=base_currency,
            to_currency="JPY",
            rate=163.25,
            rate_date=date(2024, 12, 26),
            is_updated=True,
        ),
    ]

    date_list = [rate.rate_date for rate in exc_list]
    currencies = ["JPY", "USD"]

    exc_date = date(2099, 3, 2)
    date_list.append(exc_date)
    key = exc_date.isoformat()

    exc_get, exc_get_dict = ExchangeRateProvider().get_exchange_rate(date_list, currencies)
    compare_exc(exc_list, exc_get)
    assert exc_get_dict == {"from_currency": "EUR", key: currencies}

    exc_list = [
        ExchangeRate(
            from_currency=base_currency,
            to_currency="CHF",
            rate=1.0562,
            rate_date=date(2021, 11, 1),
            is_updated=True,
        ),
    ]

    date_list = [rate.rate_date for rate in exc_list]
    currencies = [rate.to_currency for rate in exc_list]

    exc_get, exc_get_dict = ExchangeRateProvider().get_exchange_rate(date_list, currencies)
    compare_exc(exc_list, exc_get)
    assert exc_get_dict == {"from_currency": "EUR"}

    first_date = ExchangeRateProvider().minimum_available_date
    end_date = ExchangeRateProvider().maximum_available_date

    first_date = date(2000, 1, 1)
    exc_date = first_date
    date_list = []
    while exc_date <= end_date:
        date_list.append(exc_date)

        exc_date += timedelta(days=1)

    currencies = ExchangeRateProvider().available_currencies
    exc_get, exc_get_dict = ExchangeRateProvider().get_exchange_rate(date_list, currencies)

    try:
        currencies = "HRK"  # not used from 2022-12-31
        date_list = date(2025, 1, 1)
        exc_get, exc_get_dict = ExchangeRateProvider().get_exchange_rate(date_list, currencies)

    except ExchangeRateApiError as e:
        assert "Empty Response.content" == str(e)

    currencies = ["HRK", "USD"]  # HRK not used from 2022-12-31
    date_list = [date(2022, 12, 10), date(2023, 2, 1)]
    exc_get, exc_get_dict = ExchangeRateProvider().get_exchange_rate(date_list, currencies)
    assert exc_get_dict == {"from_currency": "EUR", date_list[1].isoformat(): ["HRK"]}

    try:
        currencies = ["BGN"]  # not available from 2000-07-19
        date_list = [date(2000, 1, 2)]
        exc_get, exc_get_dict = ExchangeRateProvider().get_exchange_rate(date_list, currencies)
    except ExchangeRateApiError as e:
        assert "Empty Response.content" == str(e)

    currencies = ["BGN", "USD"]  # BGN not available from 2000-07-19
    date_list = [date(2000, 7, 15), date(2000, 7, 21)]
    exc_get, exc_get_dict = ExchangeRateProvider().get_exchange_rate(date_list, currencies)
    assert exc_get_dict == {"from_currency": "EUR", date_list[0].isoformat(): ["BGN"]}


# Utils


def exc_sort_key(exc: ExchangeRate) -> tuple:
    """Keys used in the function sorted."""
    return (
        exc.from_currency,
        exc.to_currency,
        exc.rate,
        exc.rate_date,
    )


def compare_exc(exc_list, exc_get):
    exc_list = sorted(exc_list, key=exc_sort_key)
    exc_get = sorted(exc_get, key=exc_sort_key)

    assert exc_list == exc_get
