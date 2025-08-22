from src.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from src.infrastructure.sqlite.unit_of_work import UnitOfWork

# TODO: Move the location of this definition and also add direcotory
DB_PATH = "database.db"


def get_uow() -> AbstractUnitOfWork:
    uow = UnitOfWork(DB_PATH)

    try:
        return uow

    finally:
        pass
