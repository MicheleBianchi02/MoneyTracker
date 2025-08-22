from fastapi import APIRouter, Depends

from src.core.domain.category import CategoryIn, CategoryOut
from src.core.exceptions import (
    BadRequestException,
    CategoryNotFoundException,
    DuplicateCategoryException,
    InvalidCategoryError,
    ServiceCategoryNotFoundError,
    ServiceDuplicateCategoryError,
    ServiceError,
    ServiceUserNotFoundError,
    UserNotFoundException,
)
from src.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from src.core.services.category_service import CategoryService
from src.infrastructure.dependencies import get_uow

router = APIRouter(prefix="/categories", tags=["Categories"])
category_service = CategoryService()


@router.post("/", status_code=201)
def add_category(
    category: CategoryIn | list[CategoryIn],
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Adds a new category or a list of categories.
    """
    try:
        category_service.add_category(uow, category)
        return {"message": "Category added successfully."}

    except InvalidCategoryError as e:
        raise BadRequestException(str(e))
    except ServiceUserNotFoundError:
        raise UserNotFoundException()
    except ServiceDuplicateCategoryError:
        raise DuplicateCategoryException()
    except ServiceError as e:
        raise BadRequestException(str(e))


@router.get("/primary/", response_model=list[CategoryOut])
def get_primary_categories(
    id_user: int,
    year: int | None = None,
    cat_type: str | None = None,
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Retrieves a list of primary categories.
    """
    try:
        return category_service.get_primary_list(uow, id_user, year, cat_type)
    except ServiceError as e:
        raise BadRequestException(str(e))


@router.get("/secondary/", response_model=list[CategoryOut])
def get_secondary_categories(
    id_user: int,
    year: int | None = None,
    primary: str | None = None,
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Retrieves a list of secondary categories.
    """
    try:
        return category_service.get_secondary_list(uow, id_user, year, primary)
    except ServiceError as e:
        raise BadRequestException(str(e))


@router.get("/", response_model=list[CategoryOut])
def get_all_categories(
    id_user: int,
    year: int | None = None,
    cat_type: str | None = None,
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Retrieves all categories for a user.
    """
    try:
        return category_service.get(uow, id_user, year, cat_type)
    except ServiceError as e:
        raise BadRequestException(str(e))


@router.put("/{id_cat}", status_code=204)
def edit_category(id_cat: int, new_name: str, uow: AbstractUnitOfWork = Depends(get_uow)):
    """
    Edits the name of a category.
    """
    try:
        category_service.edit(uow, id_cat, new_name)
        return
    except ServiceCategoryNotFoundError:
        raise CategoryNotFoundException()
    except ServiceError as e:
        raise BadRequestException(str(e))


@router.delete("/{id_cat}", status_code=204)
def delete_category(id_cat: int, uow: AbstractUnitOfWork = Depends(get_uow)):
    """
    Deletes a category.
    """
    try:
        category_service.delete(uow, id_cat)
        return
    except ServiceCategoryNotFoundError:
        raise CategoryNotFoundException()
    except ServiceError as e:
        raise BadRequestException(str(e))
