import os

from platformdirs import PlatformDirs


class AppConfig:
    def __init__(self):
        APPNAME = "MoneyTracker"
        AUTHOR = "Nobody"

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
        self.DATA_FILE = os.path.join(data_dir, "database.db")
        self.CONFIG_FILE = os.path.join(config_dir, "server_settings.json")

    def get_data_file(self) -> str:
        """Return the database file path"""
        return self.DATA_FILE

    def get_log_file(self) -> str:
        """Return the log file path"""
        return self.LOG_FILE

    def get_config_file(self) -> str:
        """Return the config file path"""
        return self.CONFIG_FILE


app_config = AppConfig()
