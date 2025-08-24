from src.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from src.core.services.startup_config import app_config
from src.infrastructure.sqlite.unit_of_work import UnitOfWork


def get_uow() -> AbstractUnitOfWork:
    uow = UnitOfWork(app_config.get_data_file())

    try:
        return uow

    finally:
        pass
