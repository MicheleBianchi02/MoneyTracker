import logging

from src.core.domain.category import CategoryIn, CategoryOut
from src.core.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    ForeignKeyError,
    InvalidCategoryError,
    InvalidParameterError,
    OperationNotPermittedError,
    RepositoryError,
    ServiceCategoryNotFoundError,
    ServiceDuplicateCategoryError,
    ServiceError,
    ServiceUserNotFoundError,
)
from src.core.repositories.abstract_unit_of_work import AbstractUnitOfWork

logger = logging.getLogger(__name__)


class CategoryService:
    def add_category(
        self, uow: AbstractUnitOfWork, cat_list: list[CategoryIn] | CategoryIn
    ) -> None:
        """Add Category to the database.

        Parameters
        ----------
            - cat_list (list or Category) : List containing all the Category that need
                to be saved in the database.
                The argument can also be a single CategoryIn.

        Raises
        ------
            - InvalidCategoryError: If cat_type == "income" and a secondary is provided.
                Incomes can't have secondaries. Also, when the category type isn't
                'income' or 'expense'.
            - ServiceUserNotFoundError: If the provided id_user is not present in the database.
            - ServiceDuplicateCategoryError: If Unique constraint error occour (e.g. two identical
                category are inserted)
            - ServiceError: If something went wrong with the repository or the service.

        Notes
        -----
            Categories are considered unique if:
            - for primaries (secondary = None) => (id_user, year, type, primary) is
                unique in the db (name is primary in the class istance).
            - for secondaries => (id_user, year, type, primary, name) is unique in the
                db (name is secondary in the class istance).
            All those value at once need to be unique, not the single values.
            Allowed combination are:
            - Two primaries with same name but different type;
            - Multiple secondaries with the same name but different primary (each);
            - Category with the same name but different year;
            - Category with the same name but different id_user;
            - Secondary with the same name of the primary.
        """

        logger.info(f"Adding {len(list(cat_list))} categories into the database.")
        try:
            with uow:
                uow.category.add(cat_list)

        except ForeignKeyError as e:
            logger.error("The specified id_user is not present in the database")
            raise ServiceUserNotFoundError(
                "The provided id_user is not present in the database.",
            ) from e

        except InvalidParameterError as e:
            logger.error(
                "An attempt was made to add a category with type "
                "income and a non null secondary. This is not valid"
            )
            raise InvalidCategoryError(
                "An attempt was made to add a category with type "
                "income and a non null secondary. This is not valid"
            ) from e

        except DuplicateEntityError as e:
            logger.error(
                "An attemp was made to add an already existing category to the database",
            )
            raise ServiceDuplicateCategoryError(
                "An attemp was made to add an already existing category to the database",
            ) from e

        except (RepositoryError, Exception) as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def get_primary_list(
        self,
        uow: AbstractUnitOfWork,
        id_user: int,
        year: int | None,
        cat_type: str | None,
    ) -> list[CategoryOut]:
        """Get all the primary in the database with the given type.

        Parameters
        ----------
            - id_user (int) : id of the user
            - year (int or None) : year of the required category list. If None all the
                 categories for the given user (all years) are returned.
            - cat_type (str or None) : type of the category. Could be 'income' or
                'expense'. If None both types are returned.

        Returns
        -------
            A list of all the category (istance of CategoryOut) for the given year and type.
            If none are found, an empty list is returned

        Raises
        ------
            ServiceError: If something went wrong with the repository or the service.
        """

        logger.info("Getting categories primary list from the database.")

        try:
            with uow:
                return uow.category.get_primary_list(id_user, year, cat_type)

        except (RepositoryError, Exception) as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def get_secondary_list(
        self,
        uow: AbstractUnitOfWork,
        id_user: int,
        year: int | None,
        primary: str | None,
    ) -> list[CategoryOut]:
        """Get all the secondary in the database for the given primary.

        Parameters
        ----------
            - id_user (int) : id of the user
            - year (int or None) : year of the required category list. If None all
                the secondaries are returned, indipendently on the year.
            - primary (str or None) : name of the primary category parent of the required
                secondary. If None all secondary in the database are returned.
                Notes: If primary is an str argument, no control is applied if it
                really is a primary (if it doesn't exist, an empty list is returned).


        Returns
        -------
            A list of all the secondary categories )CategoryOut) for the given year and
            primary.
            If none are found, an empty list is returned.

        Raises
        ------
            ServiceError: If something went wrong with the repository or the service.
        """

        logger.info("Getting categories secondary list from the database.")

        try:
            with uow:
                return uow.category.get_secondary_list(id_user, year, primary)

        except (RepositoryError, Exception) as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def get(
        self,
        uow: AbstractUnitOfWork,
        id_user: int,
        year: int | None,
        cat_type: str | None,
    ) -> list[CategoryOut]:
        """Get all the category in the database (both primary and secondary).

        Parameters
        ----------
            - id_user (int) : id of the user
            - year (int or None) : year of the required category list. If None all the
                 categories for the given user (all years) are returned.
            - cat_type (str or None) : type of the category. Could be 'income' or
                'expense'. If None both income and expenses are returned

        Returns
        -------
            A list of all the category (CategoryOut) for the given year and type.
            If none are found, an empty list is returned

        Raises
        ------
            ServiceError: If something went wrong with the repository or the service.
        """

        logger.info("Getting categories list from the database.")

        try:
            with uow:
                return uow.category.get(id_user, year, cat_type)

        except (RepositoryError, Exception) as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def edit(self, uow: AbstractUnitOfWork, id_cat: int, new_name: str) -> None:
        """Edit a category.

        The only parameter that can be changed is the name

        Parameters
        ----------
            - id_cat (int) : id of the category to be edited
            - new_name (str) : new name of the category to be edited

        Raises
        ------
            - CategoiryNotFoundError: If the category with the given id_cat is not in the db.
            - ServiceError: If something went wrong with the repository or the service.
        """

        logger.info("Editing category")

        try:
            with uow:
                uow.category.edit(id_cat, new_name)

        except EntityNotFoundError as e:
            logger.error(f"{str(e)}")
            raise ServiceCategoryNotFoundError(
                """The category with the given id is not present in the database."""
            ) from e

        except (RepositoryError, Exception) as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def delete(self, uow: AbstractUnitOfWork, id_cat: int) -> None:
        """Delete the given category.

        Parameters
        ----------
            id_cat (int) : id of the category to be deleted

        Raises
        ------
            - CategoiryNotFoundError: If the category with the given id_cat is not in the db.
            - OperationNotPermitted: If trying to delete a primary that has some
                secondaries as child.
            - ServiceError: If something went wrong with the repository or the service.
        """

        logger.info("Editing category")

        # TODO: Change the transactions category
        try:
            with uow:
                uow.category.delete(id_cat)

        except InvalidParameterError as e:
            logger.exception(str(e))
            raise OperationNotPermittedError(
                "Cannot delete a primary with existing secondaries",
            ) from e

        except EntityNotFoundError as e:
            logger.error(f"{str(e)}")
            raise ServiceCategoryNotFoundError(
                """The category with the given id is not present in the database."""
            ) from e

        except (RepositoryError, Exception) as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e
