from typing import Literal

from fastapi import APIRouter, Depends

from moneytracker.api.dependencies import get_id_user
from moneytracker.core.domain.category import CategoryIn, CategoryOut
from moneytracker.core.exceptions import (
    BadRequestException,
    CategoryNotFoundException,
    DuplicateCategoryException,
    ForbiddenException,
    InternalServerErrorException,
    InvalidCategoryError,
    OperationNotPermittedError,
    ServiceCategoryNotFoundError,
    ServiceDuplicateCategoryError,
    ServiceError,
    ServiceUserNotFoundError,
    TransactionUseCategoryException,
    UserNotFoundException,
)
from moneytracker.core.services.category_service import CategoryService
from moneytracker.infrastructure.dependencies import get_uow
from moneytracker.infrastructure.sqlite.unit_of_work import UnitOfWork

router = APIRouter(prefix="/categories", tags=["Categories"])
category_service = CategoryService()


@router.post("/", status_code=201, response_model=None)
def add_category(
    category: list[CategoryIn],
    id_user: int = Depends(get_id_user),
    uow: UnitOfWork = Depends(get_uow),
) -> str | dict[str, str]:
    """
    Adds a new category or a list of categories.
    """
    try:
        category_service.add_category(uow, id_user, category)

        return {"message": "Category added successfully."}

    except InvalidCategoryError:
        raise BadRequestException()
    except ServiceUserNotFoundError:
        raise UserNotFoundException()
    except ServiceDuplicateCategoryError:
        raise DuplicateCategoryException()
    except ServiceError:
        raise InternalServerErrorException()


@router.get("/primary/", response_model=list[CategoryOut])
def get_primary_categories(
    year: int | None = None,
    cat_type: Literal["income", "expense"] | None = None,
    id_user: int = Depends(get_id_user),
    uow: UnitOfWork = Depends(get_uow),
):
    """
    Retrieves a list of primary categories.
    """
    try:
        return category_service.get_primary_list(uow, id_user, year, cat_type)
    except ServiceError:
        raise InternalServerErrorException()


@router.get("/secondary/", response_model=list[CategoryOut])
def get_secondary_categories(
    year: int | None = None,
    primary: str | None = None,
    id_user: int = Depends(get_id_user),
    uow: UnitOfWork = Depends(get_uow),
):
    """
    Retrieves a list of secondary categories.
    """
    try:
        return category_service.get_secondary_list(uow, id_user, year, primary)
    except ServiceError:
        raise InternalServerErrorException()


@router.get("/", response_model=list[CategoryOut])
def get_all_categories(
    year: int | None = None,
    cat_type: Literal["income", "expense"] | None = None,
    id_user: int = Depends(get_id_user),
    uow: UnitOfWork = Depends(get_uow),
):
    """
    Retrieves all categories for a user.
    """
    try:
        return category_service.get(uow, id_user, year, cat_type)
    except ServiceError:
        raise InternalServerErrorException()


@router.put("/{id_cat}", status_code=204, response_model=None)
def edit_category(
    id_cat: int,
    new_name: str,
    id_user: int = Depends(get_id_user),
    uow: UnitOfWork = Depends(get_uow),
) -> str | dict[str, str]:
    """
    Edits the name of a category.
    """
    try:
        category_service.edit(uow, id_cat, new_name, id_user)
        return {"message": "Category added successfully."}

    except ServiceCategoryNotFoundError:
        raise CategoryNotFoundException()
    except OperationNotPermittedError:
        raise ForbiddenException()
    except ServiceError:
        raise InternalServerErrorException()


@router.delete("/{id_cat}", status_code=204, response_model=None)
def delete_category(
    id_cat: int,
    id_user: int = Depends(get_id_user),
    uow: UnitOfWork = Depends(get_uow),
) -> str | dict[str, str]:
    """
    Deletes a category.
    If some transaction uses that category, it will not be deleted.
    If the category is a primary and has some secondary child, it will not be deleted.
    """
    try:
        ret = category_service.delete(uow, id_cat, id_user)

        if isinstance(ret, list):
            # TODO: return also the tr_list
            raise TransactionUseCategoryException()

        return {"message": "Category added successfully."}

    except OperationNotPermittedError:
        raise ForbiddenException()
    except ServiceCategoryNotFoundError:
        raise CategoryNotFoundException()
    except ServiceError:
        raise InternalServerErrorException()
