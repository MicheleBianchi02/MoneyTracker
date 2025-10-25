import logging
import sqlite3
from contextlib import contextmanager
from queue import Empty, Full, Queue

from moneytracker.core.services.app_config import app_config

logger = logging.getLogger(__name__)


class ConnectionPool:
    def __init__(self, db_path: str, max_connections: int = 10):
        self.db_path = db_path
        self.max_connections = max_connections
        self._pool = Queue(maxsize=max_connections)

        for _ in range(max_connections):
            try:
                conn = sqlite3.connect(db_path, check_same_thread=False, timeout=2)

                # self._connection.row_factory = sqlite3.Row

                cursor = conn.cursor()

                # TODO: These two query below can increase by a great percentage the velocity
                # of SELECT query over big number of rows. Evalueate if they are really necessary
                # and their potential problem
                cursor.execute("PRAGMA cache_size = 32768;")
                cursor.execute("PRAGMA mmap_size = 268435456;")

                cursor.execute("PRAGMA journal_mode = WAL;")

                # By default foreign_key are disable at every new connection
                cursor.execute("PRAGMA foreign_keys = ON")

                # Disable sqlite3's implicit transaction management by setting
                # isolation_level to None. This allows us to manually control
                # the transaction with BEGIN, COMMIT, and ROLLBACK.
                # Otherwise, at each INSERT, UPDATE, DELETE a new transaction is created,
                # followed by a commit/rollback.
                conn.isolation_level = None

                self._pool.put(conn, block=True)

            except Full as e:
                logger.exception(str(e))
                raise RuntimeError(f"Failed to create initial SQLite connections: {e}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get connection from the pool"""

        try:
            return self._pool.get(block=True)

        except Empty as e:
            # This should not happen since block == True
            logger.exception(str(e))
            raise RuntimeError(
                "Connection pool is empty and no connection could be retrieved.",
            )

    def _release_connection(self, conn: sqlite3.Connection) -> None:
        """Release the given connection (insert back in the pool)"""
        try:
            self._pool.put(conn, block=True)

        except Full as e:
            # This should ideally not happen if the pool is managed correctly.
            # If it does, we just close the connection.

            logger.exception(str(e))
            conn.close()

    @contextmanager
    def managed_connection(self):
        """Get database connection from the pool.

        Usage
        -----
            connection_pool = ConnectionPool(db_path)

            with connection_pool.managed_connection() as connection:
            .... # do the work here with the connection
            .... # e.g. instanciate a unit of work class

        """

        conn = self._get_connection()

        try:
            yield conn

        finally:
            self._release_connection(conn)

    def close_all(self) -> None:
        """Close all connections in the pool"""

        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Empty:
                break


logger.info("Creating database connections")
db_path = app_config.get_data_file_path()
connection_pool = ConnectionPool(db_path)
