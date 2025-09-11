from typing import Literal

from fastapi import APIRouter, Depends

from src.api.dependencies import get_id_user
from src.core.domain.category import CategoryIn, CategoryOut
from src.core.exceptions import (
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
from src.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from src.core.services.category_service import CategoryService
from src.infrastructure.dependencies import get_uow
from src.infrastructure.job_manager import COMPLETED_CODE, FAILED_CODE, UNKNOWN_CODE, check_status

router = APIRouter(prefix="/categories", tags=["Categories"])
category_service = CategoryService()


@router.post("/", status_code=201, response_model=None)
def add_category(
    category: list[CategoryIn],
    wait_response: bool = True,
    id_user: int = Depends(get_id_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> str | dict[str, str]:
    """
    Adds a new category or a list of categories.
    """
    try:
        job_id = category_service.add_category(uow, id_user, category)

        if wait_response:
            status, _ = check_status(job_id)

            if status == COMPLETED_CODE:
                return {"message": "Category added successfully."}
            elif status == FAILED_CODE or status == UNKNOWN_CODE:
                raise InternalServerErrorException(
                    f"Internal server error - job_status:{status} ",
                )

        else:
            return job_id

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
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    """
    Retrieves a list of primary categories.
    """
    try:
        return category_service.get_primary_list(uow, id_user, year, cat_type)
    except ServiceError:
        raise InternalServerErrorException


@router.get("/secondary/", response_model=list[CategoryOut])
def get_secondary_categories(
    year: int | None = None,
    primary: str | None = None,
    id_user: int = Depends(get_id_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
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
    uow: AbstractUnitOfWork = Depends(get_uow),
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
    wait_response: bool = True,
    id_user: int = Depends(get_id_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> str | dict[str, str]:
    """
    Edits the name of a category.
    """
    try:
        job_id = category_service.edit(uow, id_cat, new_name, id_user)
        if wait_response:
            status, _ = check_status(job_id)

            if status == COMPLETED_CODE:
                return {"message": "Category added successfully."}
            elif status == FAILED_CODE or status == UNKNOWN_CODE:
                raise InternalServerErrorException(
                    f"Internal server error - job_status:{status} ",
                )

        else:
            return job_id

    except ServiceCategoryNotFoundError:
        raise CategoryNotFoundException()
    except OperationNotPermittedError:
        raise ForbiddenException()
    except ServiceError:
        raise InternalServerErrorException()


@router.delete("/{id_cat}", status_code=204, response_model=None)
def delete_category(
    id_cat: int,
    wait_response: bool = True,
    id_user: int = Depends(get_id_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> str | dict[str, str]:
    """
    Deletes a category.
    If some transaction uses that category, it will not be deleted.
    If the category is a primary and has some secondary child, it will not be deleted.
    """
    try:
        ret = category_service.delete(uow, id_cat, id_user)

        if isinstance(ret, list):
            raise TransactionUseCategoryException()
        else:
            job_id = ret

        if wait_response:
            status, _ = check_status(job_id)

            if status == COMPLETED_CODE:
                return {"message": "Category added successfully."}
            elif status == FAILED_CODE or status == UNKNOWN_CODE:
                raise InternalServerErrorException(
                    f"Internal server error - job_status:{status} ",
                )

        else:
            return job_id

    except OperationNotPermittedError:
        raise ForbiddenException()
    except ServiceCategoryNotFoundError:
        raise CategoryNotFoundException()
    except ServiceError:
        raise InternalServerErrorException()
