from src.api import main
from src.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from src.infrastructure.sqlite.unit_of_work import UnitOfWork


def get_uow() -> AbstractUnitOfWork:
    uow = UnitOfWork(main.DATA_FILE)

    try:
        return uow

    finally:
        pass
