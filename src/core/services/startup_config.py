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

        self.LOG_FILE = os.path.join(log_dir, "app.log")
        # Used when generating UnitOfWork instances
        self.DATA_FILE = os.path.join(data_dir, "database.db")

    def get_data_file(self) -> str:
        return self.DATA_FILE

    def get_log_file(self) -> str:
        return self.LOG_FILE


app_config = AppConfig()
