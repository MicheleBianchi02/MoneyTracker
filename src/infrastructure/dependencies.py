from contextlib import contextmanager

from src.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from src.infrastructure.connection_pool import connection_pool
from src.infrastructure.sqlite.unit_of_work import UnitOfWork


def get_uow() -> AbstractUnitOfWork:
    """Provides a Unit of Work instance with a connection from the pool.
    This funciton is suppose to be used only with fastAPI inside Depends(get_uow())
    since it run automatically the teardown code (release the connection back
    to the pool). next(get_uow()) can also be used, but the connection is never
    released, even if the uow is deleted."""

    with connection_pool.managed_connection() as connection:
        uow = UnitOfWork(connection)

        yield uow


@contextmanager
def manage_uow() -> AbstractUnitOfWork:
    """Provide a Unit of Work instance with a connection from the pool.
    The connection is released when the __exit__ method is called (ie
    when exiting the with statement.

    Usage
    -----

        >>> connection_pool = ConnectioPool(db_path)
        >>> with manage_uow() as uow:
        ...     use uow eg in the service
        ...     or:
        ...     with uow:
        ...         do stuff

    """
    with connection_pool.managed_connection() as connection:
        uow = UnitOfWork(connection)
        yield uow
