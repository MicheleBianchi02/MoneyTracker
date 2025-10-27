import calendar
import logging
from collections import defaultdict
from datetime import date, timedelta

from moneytracker.core.domain.exchange_rate import Currency, ExchangeRate
from moneytracker.core.exceptions import (
    ApiError,
    ConnectionApiError,
    RepositoryError,
    ServiceError,
    TimeOutApiError,
)
from moneytracker.core.services.app_setting_service import AppSettingService
from moneytracker.infrastructure.dependencies import manage_uow
from moneytracker.infrastructure.exchange_rate_provider.exchange_rate import ExchangeRateProvider
from moneytracker.infrastructure.job_manager import complete_task
from moneytracker.infrastructure.sqlite.unit_of_work import UnitOfWork
from moneytracker.infrastructure.worker import (
    ADD_APP_SETTING_TASK_NAME,
    ADD_EXC_RATE_TASK_NAME,
    EDIT_EXC_RATE_TASK_NAME,
    EXC_DATE_CONFIG_NAME,
)

logger = logging.getLogger(__name__)


class ExchangeRateService:
    def __init__(self) -> None:
        exc_provider = ExchangeRateProvider()

        app_setting_service = AppSettingService()

        with manage_uow() as uow:
            self._currencies = app_setting_service.get_currencies(uow, is_active=None)

        self._active_currencies = []
        self._not_active_currencies = []
        for curr in self._currencies:
            if curr.is_active:
                self._active_currencies.append(curr)
            else:
                self._not_active_currencies.append(curr)

        self._active_codes = [curr.code for curr in self._active_currencies]

        self._max_date = exc_provider.maximum_available_date

    def validate_currency(self, currency: str) -> bool:
        """Validate if the given currency is in the list
        of active currencies.

        Parameters
        ----------
            currency (str) : currency formatted as the ISO standard (ie 'EUR', 'USD'...)

        Returns
        -------
            True if the currency is valid, false otherwise.

        """
        if currency in self._active_codes:
            return True
        else:
            return False

    def add_exchange_rate(self, uow: UnitOfWork) -> date:
        """Add exchange rates to the database at startup.

        If no rate is present in the database, a starting date is chosen, corresponding to
        firt date of the year (if the current date is to close to the yyyy-01-01 the previous
        year is chosen) and the rates are added starting from that date until the current
        date. This starting date is saved, in iso format, in the app_setting table of the db.
        At next startup, the rates are added stating from the latest date present in the db
        until the current date. If, at first startup, something went wrong with the rates
        provider (e.g. no internet connection), rates are not added to the db. It is only
        saved the starting date in the app_setting table of the db. In that case the rates
        will be added the next startup.

        Returns:
            The starting date (datetime.date) is returned.

        """

        logger.info("Adding new exchange rates to the database")

        exc_provider = ExchangeRateProvider()
        from_currency = exc_provider.base_currency

        max_date = self.maximum_available_date

        app_setting_service = AppSettingService()
        currencies = app_setting_service.get_currencies(uow, is_active=True)

        currencies = [curr.code for curr in currencies]
        currencies.remove(from_currency)

        try:
            with uow:
                today = date.today()
                latest_exc = uow.exchange_rate.get_closest(today)

                if latest_exc:
                    start_date = latest_exc[0].rate_date + timedelta(days=1)

                    if start_date >= max_date:
                        # When start_date = max_date
                        logger.info("Adding 0 new exchange rates")
                        logger.info("Adding exchange rate's operation terminated successfully")
                        return start_date

                else:
                    start_date = uow.app_setting.get(EXC_DATE_CONFIG_NAME)

                    if start_date is None:
                        year = date.today().year

                        start_date = date(year, 1, 1)

                        day_diff = (date.today() - start_date).days
                        if day_diff <= 1:
                            start_date = date(year - 1, 1, 1)

                        first_date_str = start_date.isoformat()

                        logger.info(
                            f"Exchange rates starting date not present. "
                            f"Adding {first_date_str} to the config table"
                        )
                        args = (EXC_DATE_CONFIG_NAME, first_date_str)
                        complete_task(ADD_APP_SETTING_TASK_NAME, args)

                    else:
                        start_date = date.fromisoformat(start_date)

                date_list = []
                exc_date = start_date
                while exc_date < max_date:
                    date_list.append(exc_date)
                    exc_date += timedelta(days=1)

                try:
                    exc_rates, not_available_exc = exc_provider.get_exchange_rate(
                        date_list,
                        currencies,
                    )

                except ApiError as e:
                    if isinstance(e, (TimeOutApiError, ConnectionApiError)):
                        logger.error(str(e))  # only the message
                    else:
                        logger.exception(str(e))

                    # if no connection is present, add all rates as not updated.
                    # See docs

                    exc_rates = []
                    not_available_exc = {}

                    not_available_exc = {"from_currency": exc_provider.base_currency}

                    for exc_date in date_list:
                        not_available_exc[exc_date.isoformat()] = currencies

                # In some cases, the exchange rates are not available even if everything
                # is ok with the server (e.g. for withdrawn currencies like LTL or LVL)
                # This should not happen since we are asking only for active currencies.
                # We still leave this part because of safety reason. Also because a
                # currency can get deprecated and may not detect it for a certain
                # period. So this is needed also when no exception is raised from the
                # provider.
                if len(not_available_exc.keys()) != 1:
                    from_currency = not_available_exc["from_currency"]
                    del not_available_exc["from_currency"]

                    for exc_date, curr_list in not_available_exc.items():
                        exc_date = date.fromisoformat(exc_date)

                        for curr in curr_list:
                            exc = ExchangeRate(
                                from_currency=from_currency,
                                to_currency=curr,
                                rate=1,
                                rate_date=exc_date,
                                is_updated=False,
                            )

                            exc_rates.append(exc)

                if exc_rates:
                    logger.info(f"Adding {len(exc_rates)} new exchange rates")
                    args = (exc_rates,)
                    complete_task(ADD_EXC_RATE_TASK_NAME, args)

                else:
                    logger.info("No new exchange rates have been found")

            logger.info("Adding exchange rate's operation terminated successfully")

            return start_date

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def update_exchange_rate(self, uow: UnitOfWork) -> None:
        """Updated exchange rates present in the database."""

        logger.info("Updating old exchange rates")

        exc_provider = ExchangeRateProvider()

        try:
            with uow:
                not_updated_rates = uow.exchange_rate.get_not_updated(None, None)

                not_updated_dict = defaultdict(set)
                # Assuming all exchange rates have the same from_currency
                for exc in not_updated_rates:
                    exc_date = exc.rate_date.isoformat()
                    not_updated_dict[exc_date].add(exc.to_currency)

                currencies_to_dates = defaultdict(list)
                for date_str, currency_list in not_updated_dict.items():
                    currency_key = frozenset(currency_list)
                    currencies_to_dates[currency_key].append(date.fromisoformat(date_str))

                exc_rates = []
                for currency_key, date_list in currencies_to_dates.items():
                    currency_list = list(currency_key)

                    try:
                        exc_rates_get, not_updated_rates = exc_provider.get_exchange_rate(
                            date_list, currency_list
                        )

                        exc_rates.extend(exc_rates_get)

                    except ApiError as e:
                        if isinstance(e, (TimeOutApiError, ConnectionApiError)):
                            logger.error(str(e))  # only the message
                        else:
                            logger.exception(str(e))

                logger.info(f"Updating {len(exc_rates)} exchange rates")
                if exc_rates:
                    args = (exc_rates,)
                    complete_task(EDIT_EXC_RATE_TASK_NAME, args)

            logger.info("Exchange rate's update terminated successfully")

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def get_missing_rates(
        self,
        uow: UnitOfWork,
        date_list: list[date],
    ) -> list[ExchangeRate]:
        """Get missing exchange rates based on the given date_list"""

        # This function will work only if in the database we always add the same number
        # of exchange rates (with the same number of currencies) for each date. Also, all
        # those exchange rates must have the same from_currency parameter.

        exc_pr = ExchangeRateProvider()

        # When the application is first run, exchange rates from a given starting date
        # to the given date are added. This below get this first date. From there, we are
        # sure that the exchange rates exist. If, for any reason, that date is not
        # present in the datebase, we add them now. This should never happen. It is
        # added here only for safety reason. If the rates are not present and the
        # user ask for the transaction in a different currency, there will be a problem.
        exc_starting_date = uow.app_setting.get(EXC_DATE_CONFIG_NAME)
        if exc_starting_date is None:
            exc_starting_date = self.add_exchange_rate(uow)

        else:
            exc_starting_date = date.fromisoformat(exc_starting_date)

        date_to_check = set()  # set to remove duplicate
        for tr_date in date_list:
            if tr_date >= exc_starting_date:
                continue

            elif tr_date < exc_pr.minimum_available_date:
                continue

            else:
                # dates between minimum_date (2001-01-01) and the starting date.
                # In those cases we add exchange rates only for a given range (month)

                # Can't do tr_date.replace(days=1) since the tr_date point to the original
                # list of transactions
                date_check = date(tr_date.year, tr_date.month, 1)

                date_to_check.add(date_check)

        date_to_check = list(date_to_check)
        missing_dates = uow.exchange_rate.get_missing_rates_dates(date_to_check)

        required_dates = set()  # set to remove duplicate
        exc_rates = []
        if missing_dates:
            for exc_date in missing_dates:
                year = exc_date.year
                month = exc_date.month
                last_day = calendar.monthrange(year, month)[1]
                month_date_list = [date(year, month, day) for day in range(1, last_day + 1)]

                required_dates.update(month_date_list)

            required_dates = list(required_dates)

            # this contain also the from_currency parameter.
            active_currencies = self.active_currencies

            try:
                exc_rates, not_available_exc = exc_pr.get_exchange_rate(
                    required_dates, active_currencies
                )
            except ApiError as e:
                if isinstance(e, (TimeOutApiError, ConnectionApiError)):
                    logger.error(str(e))  # only the message
                else:
                    logger.exception(str(e))

                exc_rates = []
                # Enter, for instance when there is no internet connection
                not_available_exc = {}
                not_available_exc["from_currency"] = exc_pr.base_currency
                active_currencies.remove(not_available_exc["from_currency"])

                for exc_date in missing_dates:
                    exc_date = exc_date.isoformat()
                    not_available_exc[exc_date] = active_currencies

            if len(not_available_exc.keys()) != 1:
                from_currency = not_available_exc["from_currency"]
                del not_available_exc["from_currency"]

                for exc_date, curr_list in not_available_exc.items():
                    exc_date = date.fromisoformat(exc_date)
                    cl_rate_list = uow.exchange_rate.get_closest(exc_date)

                    if cl_rate_list:
                        for cl_rate in cl_rate_list:
                            if cl_rate.to_currency in curr_list:
                                exc = ExchangeRate(
                                    from_currency=from_currency,
                                    to_currency=cl_rate.to_currency,
                                    rate=cl_rate.rate,
                                    rate_date=exc_date,
                                    is_updated=False,
                                )

                                exc_rates.append(exc)

                    else:
                        # if empty, i.e. there isn't any exchange rate in the db

                        for curr in curr_list:
                            exc = ExchangeRate(
                                from_currency=from_currency,
                                to_currency=curr,
                                rate=1,
                                rate_date=exc_date,
                                is_updated=False,
                            )

                            exc_rates.append(exc)

        return exc_rates

    def get_rate(
        self,
        uow: UnitOfWork,
        begin_date: date | None,
        end_date: date | None,
        from_currency: str | None = None,
        to_currency: str | None = None,
    ) -> list[ExchangeRate]:
        """Get the exchange rate for a given date range.

        Parameters
        ----------
            - begin_date (datetime.date or None) : starting date of the range. If None
                the lower limit is not set.
            - end_date (datetime.date or None) : end date of the range. If None, the
                upper limit is not set.
            - from_currency (str or None) : currency from which to convert. If None, all
                the exchange rate are returned. The default value is None.
            - to_curency (str or None) :

        Returns
        -------
            A list of all the exchange rate for the given range.
            The length of the list is the same as the number of currencies saved in the
            database.

        Raises
        ------
            ServiceError: If something went wrong with the repository or the service.
        """

        logger.debug("Getting exchange rates range")
        try:
            with uow:
                return uow.exchange_rate.get_range(begin_date, end_date, from_currency, to_currency)

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    @property
    def maximum_available_date(self) -> date:
        """Maximum date for which exchange rates are not available.
        If today is 01-12, exchange rate are not available for
        01-12 and 01-11.
        To get this value, the system time is used. If it isn't correct it can lead
        to some problems."""

        return self._max_date

    @property
    def active_currencies(self) -> list[str]:
        """Active currencies code."""
        return [curr.code for curr in self._active_currencies]

    @property
    def active_currencies_detailed(self) -> list[Currency]:
        """Active currencies (istances of Currency)."""
        return [curr.model_copy() for curr in self._active_currencies]

    @property
    def non_active_currencies(self) -> list[str]:
        """Non active currencies (istances of Currency)."""
        return [curr.code for curr in self._not_active_currencies]

    @property
    def non_active_currencies_detailed(self) -> list[Currency]:
        """Non active currencies (istances of Currency)."""
        return [curr.model_copy() for curr in self._not_active_currencies]
