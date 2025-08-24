import datetime
from datetime import date

import requests

from src.core.domain.exchange_rate import ExchangeRate
from src.core.exceptions import ExchangeRateApiError


class ExchangeRateProvider:
    _base_currency = "EUR"
    _minimum_date = date(2000, 1, 1)
    _available_currencies = [
        ("AUD", None),
        ("BGN", None),
        ("BRL", None),
        ("CAD", None),
        ("CHF", None),
        ("CNY", None),
        ("CZK", None),
        ("DKK", None),
        ("EUR", "€"),
        ("GBP", "£"),
        ("HKD", None),
        ("HRK", None),
        ("HUF", None),
        ("IDR", None),
        ("ILS", None),
        ("INR", None),
        ("JPY", "¥"),
        ("KRW", None),
        ("LTL", None),
        ("LVL", None),
        ("MXN", None),
        ("MYR", None),
        ("NOK", None),
        ("NZD", None),
        ("PHP", None),
        ("PLN", None),
        ("RON", None),
        ("SEK", None),
        ("SGD", None),
        ("TRY", None),
        ("USD", "$"),
        ("ZAR", None),
    ]

    @property
    def base_currency(self) -> str:
        """Base currency. Parameter of the API"""
        return self._base_currency

    @property
    def available_currencies_detailed(self) -> list[tuple[str, str | None]]:
        """Available currencies code + symbol. Parameter of the API"""
        return self._available_currencies.copy()

    @property
    def available_currencies(self) -> list[str]:
        """Available currencies code. Parameter of the API"""
        return [curr[0] for curr in self._available_currencies]

    @property
    def minimum_available_date(self) -> date:
        """Minimum date for which exchange rates are available.
        It is 2000-01-01."""
        return self._minimum_date

    @property
    def maximum_available_date(self) -> date:
        """Maximum date for which exchange rates are not available.
        If today is 01-12, exchange rate are not available for
        01-12 and 01-11."""

        # The library datetime uses the date of the system. So there could be errors
        # if the system is not updated
        return date.today() - datetime.timedelta(days=1)

    def get_exchange_rate(
        self,
        exc_date_list: list[date] | date,
        currencies: list[str] | str,
    ) -> tuple[list[ExchangeRate], dict[str, date | None | str]]:
        """Get exchange rates for the give date and currencies.

        Parameters
        ----------
            - exc_date_list (list or date) : list of all dates for which the exchange
                rate is required. It can also be a date (not a list).
            - currencies (list or str) : list of all the currencies for which the
                exchange rate is required. It can also be a str (not a list).

        Returns
        -------
            - A list of ExchangeRates instances in case the exchange rates has been found.
            - In case an exchange rate isn't found, a dictionary is returned with as keys
                the corresponding date and as values the currency list. An example of
                this can be when the date > today. Indipendently on the number of not
                available dates, the dictionary contain a 'from_currency' keys (always
                present). The format is as follow:

                # {
                #     'from_currency': 'EUR',
                #     '2035-01-01': ['USD', 'CAD', 'JPY'],
                #     '2055-10-25': ['USD', 'CAD', 'JPY'],
                # }

        Raise
        -----
            ExchangeRateApiError: when an error occour while fetching data from the
                external API (e.g. when there is not internet connection).
        """

        # Since "EUR" is used as base_currency, even if required ("EUR" in currencies)
        # no exchange rate will be returned for that currency. This is because it would
        # only be used when converting from EUR to EUR, which is completely useless.
        # Otherwise each exchange rate with to_currency = base_currency would have
        # rate = 1, which only occupy space.

        if not isinstance(exc_date_list, list):
            exc_date_list = [exc_date_list]

        if not isinstance(currencies, list):
            if currencies == self.base_currency:
                conversion_rate_dict = {}
                conversion_rate_dict["from_currency"] = self.base_currency
                return [], conversion_rate_dict

            currencies = [currencies]

        return self._get_range_exchange_rate(exc_date_list, currencies)

    def _get_range_exchange_rate(
        self,
        date_list: list[date],
        currencies: list[str],
    ) -> tuple[list[ExchangeRate], dict[str, date | None | str]]:
        # Attention: To get correct results, currencies must not contain the base_currency
        # and there should not be any duplicate

        # Remove possible duplicate. Remove also the base currency, if present (discard
        # will not raise any error if base_currency is not present)
        currencies = set(currencies)
        currencies.discard(self.base_currency)
        currencies = list(currencies)

        # Remove duplicate dates
        # sorted will transform it back to a list.
        date_list = set(date_list)

        try:
            # We need the first and last date of the range. For that we sort them and take
            # the respective element. The sorted list is also needed later.
            date_list = sorted(date_list)  # ascending order, smallest at the beginning

            # start_date is the first (smallest) date of the range (different from the
            # smallest element of date_list since _get_dates decrease it by day_range days)
            # end_date is the last (biggest) date of the range (is the same as the biggest
            # date in date_list)
            start_date, start_date_is_valid = self._get_dates(date_list[0])
            end_date = date_list[-1]
            _, end_date_is_valid = self._get_dates(end_date)

            # We don't exclude all dates just because the start_date is not valid, since
            # it can be lower than the possible values (i.e. 2000-01-01)

            # TODO:: Is this the best way to do this?????
            out_range_date: list[date] = []

            # from below:
            while not start_date_is_valid:
                out_range_date.append(date_list.pop(0))

                if date_list:
                    # if not empty.
                    start_date, start_date_is_valid = self._get_dates(date_list[0])
                else:
                    break

            # from above:
            while not end_date_is_valid and date_list:
                out_range_date.append(date_list.pop(-1))

                if date_list:
                    # if not empty.
                    end_date = date_list[-1]
                    _, end_date_is_valid = self._get_dates(end_date)
                else:
                    break

            if not date_list:
                # if empty.

                conversion_rate_dict = {}
                conversion_rate_dict["from_currency"] = self.base_currency

                for exc_date in out_range_date:
                    exc_date = exc_date.isoformat()
                    conversion_rate_dict[exc_date] = currencies

                return [], conversion_rate_dict

            # API require that currencies are given as "USD+EUR+CAD+NYZ"...
            currency = "+".join(currencies)

            start_date = start_date.isoformat()
            end_date = end_date.isoformat()

            # with detail=dataonly the json file given is smaller
            url = (
                f"https://data-api.ecb.europa.eu/service/data/EXR/"
                f"D.{currency}.{self.base_currency}.SP00.A?"
                f"startPeriod={start_date}&endPeriod={end_date}"
                "&detail=dataonly&format=jsondata"
            )

            response = requests.get(url, timeout=5)

            if response.status_code != 200:
                raise ExchangeRateApiError(
                    f"Response.status_code != 200. Returned status_code:{response.status_code}",
                )
            data = response

            if not response.content:
                # if the Content-Length==0 (response.content=b'') enter. It means
                # that the response is empty. This happen, for instance when the
                # date is bigger than the current date or in the server that
                # value is not present (e.g. for weekend days). If this is the
                # case response.json() whould give error

                raise ExchangeRateApiError("Empty Response.content")

            data = response.json()

            # each date is in iso format: "2008-12-29"
            returned_date_list = [
                (idx, d["name"])
                for idx, d in enumerate(data["structure"]["dimensions"]["observation"][0]["values"])
            ]

            # Sometimes the date can be unsorted. The index in conversion_dict will also
            # be sparse with the same order, depending on the currency. Even if the
            # returned date are not sorted, the index 0 will correspond to first date
            # in the unsorted returned date list. See docs
            returned_date_list = sorted(returned_date_list, key=lambda x: x[1])

            # Find where the date are. The output of the request are indexed
            # as number ("0", "1", ...). So we need to find these indexes.
            # The output of the API give also the dates (they are in
            # returned_date_list). When the required date (in date_list) is
            # greater than the date found in returned_date_list we save the
            # previous index (and also the corresponding date of date_list).
            # We don't do date == date_list[i] because the date may not
            # exist in the output of the API (because for instance in weekends
            # or other holidyas).

            # Supposing date_list contain yyyy-12-25, yyyy-12-26 and yyyy-12-27.
            # The returned date will be something like ... yyyy-12-24, yyyy-12-27
            # because of chistmas holidays. For the first two the rate that wil be used
            # the one of yyyy-12-24. Instead, for the last one, the correct value is
            # the one of yyyy-12-27.

            # When exchange rate for that currency are not available below a given date
            # the date is not returned. See docs

            j = 0
            while returned_date_list[j][1] > date_list[j].isoformat():
                out_range_date.append(date_list.pop(0))
                j += 1

            index_list: list[tuple[int, date]] = []
            j = 0
            ret_len = len(returned_date_list) - 1  # last index
            ret_date = returned_date_list[j][1]
            for exc_date in date_list:
                while ret_date < exc_date.isoformat() and j < ret_len:
                    j += 1
                    ret_date = returned_date_list[j][1]

                if ret_date == exc_date.isoformat() or j == ret_len:
                    # if on j is needed because if the biggest returned date < last date
                    # in date_list, the last returned date is the correct value.
                    index_list.append((returned_date_list[j][0], exc_date))

                else:
                    j -= 1
                    ret_date = returned_date_list[j][1]
                    index_list.append((returned_date_list[j][0], exc_date))

            # ------------------Create the output:
            conversion_rate_list = []
            out_range_rate = {}
            out_range_rate["from_currency"] = self.base_currency

            # Get the currency list ordered as the output of the request.
            # i.e. alphabetically (could be different from the input currensies)
            currency_list = [
                curr["id"] for curr in data["structure"]["dimensions"]["series"][1]["values"]
            ]

            # If exchange rate are not available in that date range with that currency,
            # the currency is not returned
            for curr in currencies:
                if curr not in currency_list:
                    for _, exc_date in index_list:
                        key = exc_date.isoformat()
                        out_range_rate.setdefault(key, [])
                        out_range_rate[key].append(curr)

            for i, curr in enumerate(currency_list):
                # Get all the rate of the last available day
                position = f"0:{i}:0:0:0"

                # The data are given as dictionaries where each keys correspond
                # to the index in index_list
                conversion_dict = data["dataSets"][0]["series"][position]["observations"]

                # Can't use the first and last keys since the index can be unsorted. See
                # docs (or above on sorting returned_date_list)
                # get last key
                max_idx = max(map(int, conversion_dict))
                # get first key
                min_idx = min(map(int, conversion_dict))

                for idx, exc_date in index_list:
                    # print(idx, exc_date, curr, min_idx, max_idx)
                    if idx < min_idx or idx > max_idx:
                        key = exc_date.isoformat()
                        out_range_rate.setdefault(key, [])
                        out_range_rate[key].append(curr)
                    else:
                        # keys are str not int in dictionaries
                        # None is the default value if the index is missing. See docs
                        exchange_rate = conversion_dict.get(str(idx), [None])[0]

                        # If the value is null we take the previous one. If that
                        # is null we take the previous one and so on.
                        j = idx - 1
                        while exchange_rate is None and j >= 0:
                            exchange_rate = conversion_dict.get(str(idx), [None])[0]
                            j -= 1

                        # i.e. j < 0
                        if exchange_rate is None:
                            key = exc_date.isoformat()
                            out_range_rate.setdefault(key, [])
                            out_range_rate[key].append(curr)

                        else:
                            exc = ExchangeRate(
                                from_currency=self.base_currency,
                                to_currency=curr,
                                rate=exchange_rate,
                                rate_date=exc_date,
                                is_updated=True,
                            )

                            conversion_rate_list.append(exc)

                # Fill the list whit the date that are outside the
                # correct range (i.e. days where exchange rates are not
                # available).
                for wrong_date in out_range_date:
                    key = wrong_date.isoformat()
                    out_range_rate.setdefault(key, [])
                    out_range_rate[key].append(curr)

            return conversion_rate_list, out_range_rate

        except requests.exceptions.RequestException as e:
            raise ExchangeRateApiError("Error while fetching exchange_rates") from e

    def _get_dates(self, exc_date: date, day_range: int = 7) -> tuple[date, bool]:
        """Return the required begin date of the date range.

        Return the begin_date of the date range and if that date is valid.
        If it's valid it is True, else False is returned.
        """
        begin_date = exc_date - datetime.timedelta(days=day_range)

        if exc_date >= self.maximum_available_date or exc_date < self._minimum_date:
            is_valid = False

        else:
            is_valid = True

        return begin_date, is_valid
