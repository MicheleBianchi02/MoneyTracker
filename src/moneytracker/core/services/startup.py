import json
import logging
import logging.config
import os
import socket
import threading

from moneytracker.core.exceptions import (
    ServiceError,
)
from moneytracker.core.services.exc_rate_service import ExchangeRateService
from moneytracker.core.services.healt_check_service import check_deprecated
from moneytracker.core.services.startup_config import app_config
from moneytracker.infrastructure.dependencies import manage_uow
from moneytracker.infrastructure.sqlite.initializer import initialize_database
from moneytracker.infrastructure.worker import (
    writer_worker,
)

# If the server is kept running, the exchange rates need to be updated after a given time.
EXC_ADD_INTERVAL_SECONDS = 10 * 60 * 60  # 10 hours


HOST_KEY = "host"
PORT_KEY = "port"
LOG_LEVEL_KEY = "log_level"  # log level for uvicorn, not the server
TUI_MODE_KEY = "tui_mode"


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
            daemon=False,  # closed at sthutdown
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
