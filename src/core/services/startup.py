import json
import logging
import logging.config
import os
import socket
import threading
from collections import defaultdict
from datetime import date, timedelta

from core.domain.exchange_rate import ExchangeRate
from core.exceptions import (
    ExchangeRateApiError,
    RepositoryError,
    ServiceError,
)
from core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from core.services.startup_config import app_config
from infrastructure.dependencies import manage_uow
from infrastructure.exchange_rate_provider.exchange_rate import ExchangeRateProvider
from infrastructure.job_manager import complete_task
from infrastructure.sqlite.initializer import initialize_database
from infrastructure.worker import (
    ADD_APP_CONFIG_TASK_NAME,
    ADD_EXC_RATE_TASK_NAME,
    EDIT_EXC_RATE_TASK_NAME,
    writer_worker,
)

# This is the name of the column saved in the database. It contains the starting date
# from which the exchange rate started to get saved. This string should never change.
EXC_DATE_CONFIG_NAME = "continuous_exchange_rate_start_date"

# If the server is kept running, the exchange rates need to be updated after a given time.
EXC_ADD_INTERVAL_SECONDS = 10 * 60 * 60  # 10 hours


HOST_KEY = "host"
PORT_KEY = "port"
LOG_LEVEL_KEY = "log_level"  # log level for uvicorn, not the server
TUI_MODE_KEY = "tui_mode"

# TODO: If the exchange rates for some currencies will never be found (eg for withdrawn
# currencies like LTL or LVL) we are continuing to add not_updated exchange rate with
# value = 1 into the database. This is not the best, because after it we are trying to
# updated them. This add useless data to the database. Also, those rates will always
# have rate = 1. That make them unusable. Decide if it's better to remove them or to
# add some custom behaviour to them (considering the currency and the date)
# For old one it is ok to remove them since they will never be used. Maybe it can be
# usefull to add a custom feature that permit to use them is some ways (like converting
# past transaction in those currencies to the defualt one).
# For currencies that will be withdrawn in the future it's not possible to know it now.


logger = logging.getLogger(__name__)


def bootstrap_app() -> dict[str, str]:
    """Handle application startup configuration.
    The configuration file in the config folder is read (if not present it's created)
    and the read settings are returned. If the host is null, the localhost "127.0.0.1" is
    used. If the port is null, the port will be found automatically, in the dictionary
    the value is represented as a string, not a int. If the log_level is null, "info"
    is used.
    """

    log_file = app_config.get_log_file()

    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S%z",  # z is the the offset to the UTC time in hours
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                # "level": "INFO",
                # "level": "WARNING",
                "level": "CRITICAL",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": f"{log_file}",
                "maxBytes": 1024 * 1024 * 5,  # 5 MB
                "backupCount": 5,
                "formatter": "detailed",
                "level": "INFO",
            },
        },
        "loggers": {
            "": {  # root logger
                "handlers": ["console", "file"],
                "level": "INFO",
            },
        },
    }

    logging.config.dictConfig(LOGGING_CONFIG)

    config_file = app_config.get_config_file()

    default_setting = {
        HOST_KEY: None,
        PORT_KEY: None,
        LOG_LEVEL_KEY: None,
        TUI_MODE_KEY: None,
    }

    if not os.path.exists(config_file):
        with open(config_file, "w") as f:
            json.dump(default_setting, f)

    try:
        with open(config_file, mode="r") as file:
            settings: dict = json.load(file)

        if (
            HOST_KEY not in settings
            or PORT_KEY not in settings
            or LOG_LEVEL_KEY in settings
            or TUI_MODE_KEY in settings
        ):
            # reading was successfull (no problem with the json) but a parameter is
            # missing
            with open(config_file, mode="w") as file:
                # with "w" the file content is already deleted

                settings[HOST_KEY] = settings.get(HOST_KEY, None)
                settings[PORT_KEY] = settings.get(PORT_KEY, None)
                settings[LOG_LEVEL_KEY] = settings.get(LOG_LEVEL_KEY, None)
                settings[TUI_MODE_KEY] = settings.get(TUI_MODE_KEY, None)

                json.dump(settings, file)

    except Exception as e:
        # enter if there is a problem with the json (eg missing })
        logger.exception(str(e))
        with open(config_file, mode="w") as file:
            json.dump(default_setting, file)
            settings = default_setting

    host = settings.get(HOST_KEY, None)
    port = settings.get(PORT_KEY, None)
    log_level = settings.get(LOG_LEVEL_KEY, None)
    tui_mode = settings.get(TUI_MODE_KEY, None)

    if host is None:
        host = "127.0.0.1"  # localhost
        settings[HOST_KEY] = host

    if port is None:
        # get an unused port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, 0))
            settings[PORT_KEY] = str(s.getsockname()[1])

    if log_level is None:
        settings[LOG_LEVEL_KEY] = "info"

    return settings


def startup() -> None:
    """Initialize the database.
    Add missing exchenge rates from a precise starting date.
    Update not updated exchange rates present in the database up to
    the above date.
    These last two processes are done in a separate thread."""

    # TODO: Since we are adding the exchange rates in a separate thread, there can be
    # problems if other processes try to write on the database while the thread is
    # adding the exchange rates. For example when a user sign up and the new username
    # and password need to be saved in the database. Or when a plugin interact with the
    # database at startup. Also happen when two different user try to write at the
    # same time. Since fastAPI create multiple thread for each user.
    # At the moment to solve this we add a timeout in the sqlite connection such
    # that no error are raised and the process wait until the lock is removed. Not
    # ideal with many users.

    try:
        # TODO: Find a better way to do this. Connection should not appear here
        with manage_uow() as uow:
            with uow:
                initialize_database(uow._connection)

        logger.info("Running startup service")

        startup_thread = threading.Thread(
            target=_fill_exch,
            daemon=True,
        )

        logger.info("Starting startup thread")
        startup_thread.start()

        worker_thread = threading.Thread(
            target=writer_worker,
            daemon=False,  # closed at sthutdown
        )

        logger.info("Starting worker thread")
        worker_thread.start()

    except Exception as e:
        logger.exception(str(e))
        raise ServiceError("An unexpected system error occurred.") from e


def _fill_exch() -> None:
    try:
        logger.info("Adding new exchange rates to the database")
        with manage_uow() as uow:
            _add_exchange_rate(uow)
        logger.info("Updating old exchange rates")
        with manage_uow() as uow:
            _update_exchange_rate(uow)

    except Exception as e:
        logger.exception(str(e))

    # After the given interval call this function again. The timer belowe
    # will create a new thread, but the first thread that call this function
    # will be closed, meaning that the number of thread will be costant
    # over time (except after this command and just before finishing
    # the function)
    threading.Timer(EXC_ADD_INTERVAL_SECONDS, _fill_exch).start()


# In the _add_exchange_rate function, if the connection isn't present (or something else
# goes wrong) the exchange rate are not added. It means that they are added only when the
# updated value is present. Not updated exchange rate can be added in that date range,
# but calling _update_exchange_rate in that date range will never update them (because
# the exchange rate is not provided by the API, ie nothing will be returned by the
# exchange rate provider).
# TODO: What happen if something went wrong with the provider and only some exchange rate
# are not provided by the API (eg the provider had some problem on certain currency
# and solve some time later, ie the exchange rate become available in the future?).
# Since each time the user uses that currency he will get a non updated warning, we can
# add a button in the settings that scan all the non updated exchange rate (indipendently
# on the date range) and try to update all the not updated exchange rate. We can also
# call _add_exchange_rate (for example when at startup the connection is not present but
# it get activated after a while => no need to close and reopen the app)
def _update_exchange_rate(uow: AbstractUnitOfWork) -> None:
    """Updated exchange rates present in the database.

    Rates to be updated are only the one up to the starting date (defined in
    _add_exchange_rate).
    """
    exc_provider = ExchangeRateProvider()

    try:
        with uow:
            first_date = uow.app_config.get(EXC_DATE_CONFIG_NAME)
            if first_date is not None:
                first_date = date.fromisoformat(first_date)

                end_date_range = first_date - timedelta(days=1)

                not_updated_rates = uow.exchange_rate.get_not_updated(None, end_date_range)

                not_updated_dict = defaultdict(set)
                # Assuming all exchange rates have the same from_currency
                for exc in not_updated_rates:
                    exc_date = exc.rate_date.isoformat()
                    not_updated_dict[exc_date].add(exc.to_currency)

                currencies_to_dates = defaultdict(list)
                for date_str, currency_list in not_updated_dict.items():
                    currency_key = frozenset(currency_list)
                    currencies_to_dates[currency_key].append(date.fromisoformat(date_str))

                # Fetch from API
                for currency_key, date_list in currencies_to_dates.items():
                    currency_list = list(currency_key)

                    try:
                        exc_rates, not_updated_rates = exc_provider.get_exchange_rate(
                            date_list, currency_list
                        )
                    except ExchangeRateApiError:
                        exc_rates = []

                    args = (exc_rates,)
                    complete_task(EDIT_EXC_RATE_TASK_NAME, args)

        logger.info("Exchange rate's update terminated successfully")

    except RepositoryError as e:
        logger.exception(str(e))
        raise ServiceError("an unexpected system error occurred.") from e


def _add_exchange_rate(uow: AbstractUnitOfWork) -> None:
    """Add exchange rates to the database at startup.

    If no rate is present in the database, a starting date is chosen, corresponding to
    firt date of the year (if the current date is to close to the yyyy-01-01 the previous
    year is chosen) and the rates are added starting from that date until the current
    date. This starting date is saved, in iso format, in the app_config table of the db.
    At next startup, the rates are added stating from the latest date present in the db
    until the current date. If, at first startup, something went wrong with the rates
    provider (e.g. no internet connection), rates are not added to the db. It is only
    saved the starting date in the app_config table of the db. In that case the rates
    will be added the next startup.
    """

    exc_provider = ExchangeRateProvider()
    max_date = exc_provider.maximum_available_date
    currencies = exc_provider.available_currencies

    try:
        with uow:
            today = date.today()
            latest_exc = uow.exchange_rate.get_closest(today)

            if latest_exc:
                start_date = latest_exc[0].rate_date + timedelta(days=1)

                if start_date < max_date:
                    date_list = []

                    exc_date = start_date
                    while exc_date < max_date:
                        date_list.append(exc_date)
                        exc_date += timedelta(days=1)

                else:
                    # When start_date = max_date
                    return

                try:
                    exc_rates, not_available_exc = exc_provider.get_exchange_rate(
                        date_list,
                        currencies,
                    )

                except ExchangeRateApiError as e:
                    logger.exception(str(e))

                    exc_rates = []
                    not_available_exc = {}

                if exc_rates:
                    # In some cases, the exchange rates are not available even if everything
                    # is ok with the server (e.g. for withdrawn currencies like LTL or LVL)
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

                    args = (exc_rates,)
                    complete_task(ADD_EXC_RATE_TASK_NAME, args)

            else:
                first_date = uow.app_config.get(EXC_DATE_CONFIG_NAME)

                if first_date is None:
                    year = date.today().year

                    first_date = date(year, 1, 1)

                    day_diff = (date.today() - first_date).days
                    if day_diff <= 1:
                        first_date = date(year - 1, 1, 1)

                    first_date_str = f"{year}-01-01"

                    args = (EXC_DATE_CONFIG_NAME, first_date_str)
                    complete_task(ADD_APP_CONFIG_TASK_NAME, args)

                # It can happen that the first_date is present in app_config even if the
                # exchange rate table is empty. For example if when the first time this function
                # is run, there is no internet connection the returned exc_rates will be empty.
                # In this case the exchange rates will be added at the next startup.

                # TODO: What happen if the user, at first starup, has no internet connection
                # and, in the same session, add some transaction in different dates in the
                # past but within the same year? And what if he call get_summary where
                # exchange rates are required? (and if the currency is always the same?)

                date_list = []

                exc_date = first_date
                while exc_date < max_date:
                    date_list.append(exc_date)
                    exc_date += timedelta(days=1)

                try:
                    exc_rates, not_available_exc = exc_provider.get_exchange_rate(
                        date_list,
                        currencies,
                    )

                except ExchangeRateApiError as e:
                    logger.exception(str(e))

                    exc_rates = []
                    not_available_exc = {}

                if exc_rates:
                    # In some cases, the exchange rates are not available even if everything
                    # is ok with the server (e.g. for withdrawn currencies like LTL or LVL)
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

                    args = (exc_rates,)
                    complete_task(ADD_EXC_RATE_TASK_NAME, args)

        logger.info("Adding exchange rate's operation terminated successfully")

    except RepositoryError as e:
        logger.exception(str(e))
        raise ServiceError("An unexpected system error occurred.") from e
