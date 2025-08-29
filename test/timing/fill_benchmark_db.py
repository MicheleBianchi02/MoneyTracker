# Run this as a module:
# From the root: python3 -m test.timing.fill_benchmark_db
# Remember to activarte venv


from datetime import timedelta

from src.infrastructure.connection_pool import ConnectionPool
from src.infrastructure.sqlite.unit_of_work import UnitOfWork
from test.util_test import UtilTest

DB_PATH = "test/timing/benchmark.db"  # same directory of the test

# NOTE: If updating the database (eg changing some table columns), delete the database

if __name__ == "__main__":
    connection_pool = ConnectionPool(DB_PATH, max_connections=1)
    with connection_pool.managed_connection() as conn:
        with UnitOfWork(conn) as uow:
            # tr_get = uow.transaction.get(1, None, None, None)
            # print(len(tr_get))
            # tr_get = uow.transaction.get(2, None, None, None)
            # print(len(tr_get))
            # tr_get = uow.transaction.get(3, None, None, None)
            # print(len(tr_get))

            UtilTest.init_database(uow)
            _, _, tr_list = UtilTest.fill_user_cat_tr(
                uow,
                n_user=3,
                n_prim=30,
                n_tr=1000000,
            )

            min_date = min(tr.tr_date for tr in tr_list)
            max_date = max(tr.tr_date for tr in tr_list)

            date_list = []

            exc_date = min_date
            while exc_date <= max_date:
                date_list.append(exc_date)
                exc_date += timedelta(days=1)

            UtilTest.add_exchange_rate(uow, tr_list=None, date_list=date_list)
