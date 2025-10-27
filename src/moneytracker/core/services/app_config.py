import json
import logging
import os
import socket

from platformdirs import PlatformDirs

APPNAME = "MoneyTracker"
AUTHOR = "Michele_Bianchi"

# The database should never change
DB_NAME = "database.db"

HOST_KEY = "host"
PORT_KEY = "port"
LOG_LEVEL_KEY = "log_level"  # log level, used both for uvicorn and the server
TUI_MODE_KEY = "tui_mode"


class AppConfig:
    def __init__(self):
        dirs = PlatformDirs(APPNAME, AUTHOR)

        data_dir = dirs.user_data_dir
        config_dir = dirs.user_config_dir
        log_dir = dirs.user_log_dir

        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

        self.LOG_FILE = os.path.join(log_dir, "app.log")
        # Used when generating db connections
        self.DATA_FILE = os.path.join(data_dir, DB_NAME)
        self.CONFIG_FILE = os.path.join(config_dir, "server_settings.json")

    def get_data_file_path(self) -> str:
        """Return the database file path"""
        return self.DATA_FILE

    def get_log_file_path(self) -> str:
        """Return the log file path"""
        return self.LOG_FILE

    def get_config_file_path(self) -> str:
        """Return the config file path"""
        return self.CONFIG_FILE

    def get_config_settings(self) -> dict:
        settings = self._open_josn()

        host = settings.get(HOST_KEY, None)
        port = settings.get(PORT_KEY, None)
        log_level = settings.get(LOG_LEVEL_KEY, None)
        tui_mode = settings.get(TUI_MODE_KEY, None)  # this is left None if not present

        if host is None:
            host = "127.0.0.1"  # localhost
            settings[HOST_KEY] = host

        if port is None:
            settings[PORT_KEY] = self._get_free_port(host)

        if log_level is None:
            settings[LOG_LEVEL_KEY] = "INFO"
        else:
            settings[LOG_LEVEL_KEY] = log_level.upper()

        return settings

    def init_loggin(self, log_level: str = "INFO") -> None:
        log_file = self.get_log_file_path()

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
                    "level": "DEBUG",
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

    def edit_config(self, key: str, value) -> None:
        config_file = self.get_config_file_path()

        settings = self._open_josn()

        settings[key] = value

        with open(config_file, mode="w") as file:
            json.dump(settings, file)

    def _open_josn(self) -> dict:
        """Open the json config file. Handle problems and missing keys."""

        config_file = self.get_config_file_path()

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
                or LOG_LEVEL_KEY not in settings
                or TUI_MODE_KEY not in settings
            ):
                # reading was successfull (no problem with the json) but a parameter is
                # missing. Can happen when this script is modified but the json file is not.
                with open(config_file, mode="w") as file:
                    # with "w" the file content is already deleted

                    settings[HOST_KEY] = settings.get(HOST_KEY, None)
                    settings[PORT_KEY] = settings.get(PORT_KEY, None)
                    settings[LOG_LEVEL_KEY] = settings.get(LOG_LEVEL_KEY, None)
                    settings[TUI_MODE_KEY] = settings.get(TUI_MODE_KEY, None)

                    json.dump(settings, file)

        except Exception:
            # enter if there is a problem with the json (eg missing })
            with open(config_file, mode="w") as file:
                json.dump(default_setting, file)
                settings = default_setting

        return settings

    def _get_free_port(self, host: str) -> str:
        # get an unused port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, 0))
            return str(s.getsockname()[1])


app_config = AppConfig()
