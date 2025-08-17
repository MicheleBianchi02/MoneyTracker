from datetime import date

from src.core.domain.exchange_rate import ExchangeRate
from src.core.exceptions import DuplicateEntityError, EntityNotFoundError
from src.core.repositories.abstract_exchange_rate_repository import AbstractExchangeRateRepository


class FakeExchangeRateRepository(AbstractExchangeRateRepository):
    def __init__(self, exchange_rates: list[ExchangeRate] | None = None):
        self._exchange_rates = exchange_rates if exchange_rates is not None else []

    def add(self, exc_list: list[ExchangeRate] | ExchangeRate) -> None:
        if not isinstance(exc_list, list):
            exc_list = [exc_list]

        for exc in exc_list:
            if any(
                e.from_currency == exc.from_currency
                and e.to_currency == exc.to_currency
                and e.rate_date == exc.rate_date
                for e in self._exchange_rates
            ):
                raise DuplicateEntityError("Exchange rate already exists.")
            self._exchange_rates.append(exc)

    def get(
        self,
        exc_date: date,
        from_currency: str | None = None,
        to_currency: str | None = None,
    ) -> list[ExchangeRate]:
        rates = [r for r in self._exchange_rates if r.rate_date == exc_date]
        if from_currency:
            rates = [r for r in rates if r.from_currency == from_currency]
        if to_currency:
            rates = [r for r in rates if r.to_currency == to_currency]
        return rates

    def get_closest(self, exc_date: date) -> list[ExchangeRate]:
        if not self._exchange_rates:
            return []

        closest_date = min(
            self._exchange_rates, key=lambda r: abs(r.rate_date - exc_date)
        ).rate_date
        return [r for r in self._exchange_rates if r.rate_date == closest_date]

    def get_not_updated(
        self,
        begin_date: date | None,
        end_date: date | None,
    ) -> list[ExchangeRate]:
        if begin_date is None:
            begin_date = date(1, 1, 1)

        if end_date is None:
            end_date = date(9999, 12, 31)
        return [
            r
            for r in self._exchange_rates
            if not r.is_updated and r.rate_date >= begin_date and r.rate_date <= end_date
        ]

    def get_missing_rates_dates(self, date_list: list[date] | date) -> list[date]:
        if not isinstance(date_list, list):
            date_list = [date_list]

        unique_dates = set(date_list)
        present_dates = {r.rate_date for r in self._exchange_rates}

        return sorted(list(unique_dates - present_dates))

    def edit(self, new_exch: ExchangeRate) -> None:
        exc = next(
            (
                e
                for e in self._exchange_rates
                if e.from_currency == new_exch.from_currency
                and e.to_currency == new_exch.to_currency
                and e.rate_date == new_exch.rate_date
            ),
            None,
        )
        if exc is None:
            raise EntityNotFoundError("Exchange rate not found.")

        exc.rate = new_exch.rate
        exc.is_updated = new_exch.is_updated

    def delete(self, exc: ExchangeRate) -> None:
        rate_to_delete = next(
            (
                e
                for e in self._exchange_rates
                if e.from_currency == exc.from_currency
                and e.to_currency == exc.to_currency
                and e.rate_date == exc.rate_date
            ),
            None,
        )
        if rate_to_delete is None:
            raise EntityNotFoundError("Exchange rate not found.")
        self._exchange_rates.remove(rate_to_delete)
