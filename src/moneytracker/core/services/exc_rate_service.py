from moneytracker.infrastructure.exchange_rate_provider.exchange_rate import ExchangeRateProvider


class ExchangeRateService:
    def __init__(self) -> None:
        exc_provider = ExchangeRateProvider()
        self._available_currencies = exc_provider.available_currencies
        self._available_currencies_detailed = exc_provider.available_currencies_detailed

    def validate_currency(self, currency: str) -> bool:
        """Validate if the given currency is in the list
        of available currencies.

        Parameters
        ----------
            currency (str) : currency formatted as the ISO standard (ie 'EUR', 'USD'...)

        Returns
        -------
            True if the currency is valid, false otherwise.

        """
        if currency in self._available_currencies:
            return True
        else:
            return False

    @property
    def available_currencies(self) -> list[str]:
        """Available currencies code. Parameter of the API"""
        return self._available_currencies.copy()

    @property
    def available_currencies_detailed(self) -> list[tuple[str, str | None]]:
        """Available currencies code + symbol. Parameter of the API"""
        return self._available_currencies_detailed.copy()


exc_rate_service = ExchangeRateService()
