from moneytracker.infrastructure.connection_pool import ConnectionPool, connection_pool
from moneytracker.infrastructure.dependencies import get_uow, manage_uow

# Attention: Just by importing the connection_pool module we are creating
# a pool since an instance of ConnectionPool is created in that script.
# We create a new one here since we want to control the number of connections


def test_connection_pool(tmp_path):
    db_path = tmp_path / "database.db"

    db_path = str(db_path)
    n_conn = 10
    connection_pool = ConnectionPool(db_path, n_conn)

    assert connection_pool._pool.qsize() == n_conn

    with connection_pool.managed_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        assert cursor.fetchone()[0] == "wal"

        cursor.execute("PRAGMA foreign_keys")
        assert cursor.fetchone()[0] == 1


def test_uow(tmp_path):
    # Since we are using the ConnectionPool istance created at startup, with the
    # default value for maximum number of connections, we need to use it also here.
    default_max_connections = ConnectionPool.__init__.__defaults__[0]

    assert connection_pool._pool.qsize() == default_max_connections

    with manage_uow() as _:
        assert connection_pool._pool.qsize() == default_max_connections - 1

    assert connection_pool._pool.qsize() == default_max_connections

    with manage_uow() as _:
        with manage_uow() as _:
            assert connection_pool._pool.qsize() == default_max_connections - 2
        assert connection_pool._pool.qsize() == default_max_connections - 1

    assert connection_pool._pool.qsize() == default_max_connections

    # check that the uow is not creating any problem (ie closing the connection)
    with manage_uow() as uow:
        with uow:
            pass

    assert connection_pool._pool.qsize() == default_max_connections
    # with get_uow() we are not releasing the connections

    uow_get_1 = get_uow()
    _ = next(uow_get_1)
    uow_get_2 = get_uow()
    _ = next(uow_get_2)
    uow_get_3 = get_uow()
    _ = next(uow_get_3)
    uow_get_4 = get_uow()
    _ = next(uow_get_4)

    assert connection_pool._pool.qsize() == default_max_connections - 4
