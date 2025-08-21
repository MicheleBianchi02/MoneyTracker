from src.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from src.core.services.category_service import CategoryService
from src.core.services.transaction_service import TransactionServices
from src.core.services.user_service import UserService
from src.core.services.user_setting_service import UserSettingService
from src.infrastructure.sqlite.unit_of_work import UnitOfWork

# TODO: Move the location of this definition
DB_PATH = "database.py"


def get_uow() -> AbstractUnitOfWork:
    uow = UnitOfWork(DB_PATH)

    try:
        yield uow

    finally:
        pass


tr_service = TransactionServices()
cat_service = CategoryService()
user_service = UserService()
user_setting_service = UserSettingService()


def get_tr_service() -> TransactionServices:
    return tr_service


def get_cat_service() -> CategoryService:
    return cat_service


def get_user_service() -> UserService:
    return user_service


def get_user_setting_service() -> UserSettingService:
    return user_setting_service
