import logging

from moneytracker.core.domain.category import CategoryIn, CategoryOut
from moneytracker.core.domain.transaction import TransactionOut
from moneytracker.core.exceptions import (
    EntityNotFoundError,
    InvalidCategoryError,
    OperationNotPermittedError,
    RepositoryError,
    ServiceCategoryNotFoundError,
    ServiceDuplicateCategoryError,
    ServiceError,
)
from moneytracker.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from moneytracker.infrastructure.job_manager import complete_task
from moneytracker.infrastructure.worker import (
    ADD_CAT_TASK_NAME,
    DELETE_CAT_TASK_NAME,
    EDIT_CAT_TASK_NAME,
)

logger = logging.getLogger(__name__)


class CategoryService:
    def add_category(
        self,
        uow: AbstractUnitOfWork,
        id_user: int,
        cat_list: list[CategoryIn] | CategoryIn,
    ) -> None:
        """Add Category to the database.

        All the categories will be added to the user with the given id_user.
        If the secondary is not None, only the primary is added. If not, the primary
        is added to the database only if not present, and then the secondary.

        Parameters
        ----------
            - id_user (int) : id of the user for which to add all the categories.
            - cat_list (list or Category) : List containing all the Category that need
                to be saved in the database.
                The argument can also be a single CategoryIn.

        Raises
        ------
            - InvalidCategoryError: If cat_type == "income" and a secondary is provided.
                Incomes can't have secondaries. Also, when the category type isn't
                'income' or 'expense' or when the primary or secondary is empty (ie "").
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
                for cat in cat_list:
                    if cat.primary == "" or cat.secondary == "":
                        logger.error("Empty category's primary or secondary is not valid")
                        raise InvalidCategoryError(
                            "Empty category's primary or secondary is not valid"
                        )

                    if cat.category_type == "income" and cat.secondary is not None:
                        logger.error(
                            "An attempt was made to add a category with type "
                            "income and a non null secondary. This is not valid"
                        )
                        raise InvalidCategoryError(
                            "An attempt was made to add a category with type "
                            "income and a non null secondary. This is not valid"
                        )

                    # TODO: This check can be improved (normally user will have very few
                    # categories, so this approach can still be reasonable in terms
                    # of performace, also considering how many categories will be
                    # added).
                    id_cat = uow.category.get_id(
                        id_user,
                        cat.year,
                        cat.category_type,
                        cat.primary,
                        cat.secondary,
                    )

                    if id_cat is not None:
                        logger.error(
                            "An attemp was made to add an already existing category to the database",
                        )
                        raise ServiceDuplicateCategoryError(
                            "An attemp was made to add an already existing category to the database",
                        )

            args = (id_user, cat_list)
            complete_task(ADD_CAT_TASK_NAME, args)

        except RepositoryError as e:
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

        except RepositoryError as e:
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

        except RepositoryError as e:
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

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def edit(self, uow: AbstractUnitOfWork, id_cat: int, new_name: str, id_user: int) -> None:
        """Edit a category.

        The only parameter that can be changed is the name. The new name can't be
        an empty string.

        Parameters
        ----------
            - id_cat (int) : id of the category to be edited
            - new_name (str) : new name of the category to be edited
            - id_user (int) : id_user of the category to be edited

        Raises
        ------
            - ServiceCategoryNotFoundError: If the category with the given id_cat is not in the db.
            - OperationNotPermittedError: If the category with id = id_cat doesn't
                have the given id_user. Also when the new_name is an empty string (ie "")
            - ServiceError: If something went wrong with the repository or the service.
        """

        logger.info("Editing category")

        try:
            with uow:
                cat_id_user = uow.category.validate_id_cat(id_cat)

            if not cat_id_user:
                logger.error(
                    f"Category with id_cat:{id_cat} doesn't exist in the database",
                )
                raise ServiceCategoryNotFoundError(
                    """The category with the given id is not present in the database."""
                )

            if cat_id_user != id_user:
                logger.error(
                    f"The category with id:{id_cat} doesn't pertain to the user with id_user:{id_user}"
                )
                raise OperationNotPermittedError("The transaction doesn't pertain to the user")

            if new_name == "":
                logger.error("Empty category's primary or secondary is not valid")
                raise InvalidCategoryError("Empty category's primary or secondary is not valid")

            args = (id_cat, new_name)
            complete_task(EDIT_CAT_TASK_NAME, args)

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def delete(
        self, uow: AbstractUnitOfWork, id_cat: int, id_user: int
    ) -> list[TransactionOut] | None:
        """Delete the given category.

        Parameters
        ----------
            - id_cat (int) : id of the category to be deleted
            - id_user (int) : id_user of the category to be edited

        Returns
        -------
            If there are transactions with that id_cat a list of TransactionOut instances
            is returned. In that case the category is not deleted. Otherwise nothing
            is returned.

        Raises
        ------
            - ServiceCategoryNotFoundError: If the category with the given id_cat is
                not in the db.
            - OperationNotPermitted: If trying to delete a primary that has some
                secondaries as child or the category doesn't have the provided id_user.
            - ServiceError: If something went wrong with the repository or the service.

        Notes
        -----
            Deleting a category is not allowed if there are transactions that uses that
            category. Also, it's not allowed if category to be deleted is a primary and
            still has secondaries as child.
        """

        logger.info("Deleting category")

        try:
            with uow:
                cat_id_user = uow.category.validate_id_cat(id_cat)

                if not cat_id_user:
                    logger.error(
                        f"Category with id_cat:{id_cat} doesn't exist in the database",
                    )
                    raise ServiceCategoryNotFoundError(
                        """The category with the given id is not present in the database."""
                    )

                if cat_id_user != id_user:
                    logger.error(
                        f"The category with id:{id_cat} doesn't pertain to the user with id_user:{id_user}"
                    )
                    raise OperationNotPermittedError("The transaction doesn't pertain to the user")

                tr_list = uow.transaction.get_by_id_cat(id_cat)

                if tr_list != []:
                    logger.info(
                        "Cannot delete category whith transactions using that category",
                    )
                    return tr_list

                sec_list = uow.category.get_secondary_list_by_id(id_cat)

                if sec_list:
                    logger.info(
                        "Cannot delete a primary with existing secondaries",
                    )
                    raise OperationNotPermittedError(
                        "Cannot delete a primary with existing secondaries",
                    )

                args = (id_cat,)
                complete_task(DELETE_CAT_TASK_NAME, args)

        except EntityNotFoundError as e:
            logger.error(f"{str(e)}")
            raise ServiceCategoryNotFoundError(
                """The category with the given id is not present in the database."""
            ) from e

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e
