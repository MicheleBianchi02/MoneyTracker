import logging
import logging.config
import threading

from moneytracker.core.exceptions import (
    ServiceError,
)
from moneytracker.core.services.app_config import LOG_LEVEL_KEY, app_config
from moneytracker.core.services.exc_rate_service import ExchangeRateService
from moneytracker.core.services.healt_check_service import check_deprecated
from moneytracker.infrastructure.dependencies import manage_uow
from moneytracker.infrastructure.sqlite.initializer import initialize_database
from moneytracker.infrastructure.worker import (
    writer_worker,
)

# If the server is kept running, the exchange rates need to be updated after a given time.
EXC_ADD_INTERVAL_SECONDS = 10 * 60 * 60  # 10 hours


logger = logging.getLogger(__name__)


def bootstrap_app() -> dict[str, str]:
    """Handle application startup configuration.
    The configuration file in the config folder is read (if not present it's created)
    and the read settings are returned. If the host is null, the localhost "127.0.0.1" is
    used. If the port is null, the port will be found automatically, in the dictionary
    the value is represented as a string, not a int. If the log_level is null, "info"
    is used.
    """

    settings = app_config.get_config_settings()

    app_config.init_loggin(settings[LOG_LEVEL_KEY])

    return settings


def startup() -> None:
    """Initialize the database.
    Add missing exchenge rates from a precise starting date.
    Update not updated exchange rates present in the database up to
    the above date.
    These last two processes are done in a separate thread."""

    logger.info("Running startup service")

    try:
        # TODO: Find a better way to do this. Connection should not appear here
        with manage_uow() as uow:
            with uow:
                initialize_database(uow._connection)

        startup_thread = threading.Thread(
            target=_fill_exch,
            daemon=True,
        )

        logger.info("Starting startup thread")
        startup_thread.start()

        worker_thread = threading.Thread(
            target=writer_worker,
            daemon=False,  # closed at shutdown
        )

        logger.info("Starting worker thread")
        worker_thread.start()

    except Exception as e:
        logger.exception(str(e))
        raise ServiceError("An unexpected system error occurred.") from e


def _fill_exch() -> None:
    try:
        logger.info("Starting routine control")
        with manage_uow() as uow:
            check_deprecated(uow)

        with manage_uow() as uow:
            ExchangeRateService().add_exchange_rate(uow)

        with manage_uow() as uow:
            ExchangeRateService().update_exchange_rate(uow)

        logger.info("Routine control completed")
    except Exception as e:
        logger.exception(str(e))

    # After the given interval call this function again. The timer below
    # will create a new thread, but the first thread that call this function
    # will be closed, meaning that the number of thread will be costant
    # over time (except after this command and just before finishing
    # the function)
    threading.Timer(EXC_ADD_INTERVAL_SECONDS, _fill_exch).start()
