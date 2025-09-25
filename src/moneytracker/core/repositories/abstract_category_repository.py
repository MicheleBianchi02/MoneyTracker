from abc import ABC, abstractmethod

from moneytracker.core.domain.category import CategoryIn, CategoryOut


class AbstractCategoryRepository(ABC):
    @abstractmethod
    def add(self, id_user: int, cat_list: list[CategoryIn] | CategoryIn) -> None:
        """Add Category to the database.

        All the categories will be added to the user with the given id_user.

        Parameters
        ----------
            - id_user (int) : id of the user for which the categories will be added.
            - cat_list (list or Category) : List containing all the Category that need
                to be saved in the database.
                The argument can also be a single CategoryIn.

        Raises
        ------
            - InvalidParameterError: If cat_type == "income" and a secondary is provided.
                Incomes can't have secondaries. Also, when the category type isn't
                'income' or 'expense'.
            - ForeignKeyError: If a foreign key error occour (e.g. a category with
                a non existing id_user is added).
            - DuplicateEntityError: If Unique constraint error occour (e.g. two identical
                category are inserted)
            - RepositoryError: If something went wrong with the database

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

        raise NotImplementedError

    @abstractmethod
    def get_primary_list(
        self,
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
            RepositoryError: If something went wrong with the database
        """

        raise NotImplementedError

    @abstractmethod
    def get_secondary_list(
        self,
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
            RepositoryError: If something went wrong with the database
        """

        raise NotImplementedError

    @abstractmethod
    def get_secondary_list_by_id(self, id_prim: int) -> list[CategoryOut]:
        """Get secondaries with primary having the given id.

        Parameters
        ----------
            id_prim (int) : id of the primary category parent of the required secondaries

        Returns
        -------
            A list of CategoryOut instances which have all the same primary id.
            If none are found, an empty list is returned

        Raise:
            - EntityNotFoundError: If the primary with the given id is not present
                in the database.
            - RepositoryError: If something went wrong with the database
        """

        raise NotImplementedError

    @abstractmethod
    def get(
        self,
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
            RepositoryError: If something went wrong with the database
        """

        raise NotImplementedError

    @abstractmethod
    def get_id(
        self,
        id_user: int,
        year: int,
        cat_type: str,
        primary: str,
        secondary: str | None,
    ) -> int | None:
        """Get the id_category of a category by name.

        Parameters
        ----------
            - id_user (int) : id of the user
            - year (int or None) : year of the required category.
            - cat_type (str) : type of the required category. Can be "income" or "expense".
            - priamry (str) : name of the primary category
            - secondary (str or None) : name of the secondary category (or subcategory)
                referring to the given primary. None if the id of the primary is required.

        Returns
        -------
            The id of the required category with the given primary, secondary (if present)
            and type.
            None is returned if no category is found.

        Raises
        ------
            RepositoryError: If something went wrong with the database
        """

        raise NotImplementedError

    @abstractmethod
    def edit(self, id_cat: int, new_name: str) -> None:
        """Edit a category.

        The only parameter that can be changed is the name.
        If the category with the given id is not present in the database,
        nothing is done.

        Parameters
        ----------
            - id_cat (int) : id of the category to be edited
            - new_name (str) : new name of the category to be edited

        Raises
        ------
            RepositoryError: If something went wrong with the database
        """

        raise NotImplementedError

    @abstractmethod
    def delete(self, id_cat: int) -> None:
        """Delete the given category.

        If the category with the given id is not present in the database,
        nothing is done.

        Parameters
        ----------
            id_cat (int) : id of the category to be deleted

        Raises
        ------
            RepositoryError: If something went wrong with the database
        """

        raise NotImplementedError

    @abstractmethod
    def validate_id_cat(self, id_cat: int) -> tuple[int, int | None] | None:
        """Check if the provided category id is present
        in the database.

        Parameters
        ----------
            id_cat (int) : id of the category

        Returns
        -------
            None if the category with the corresponding id is not found in the
            database. If present, the id_user and the parent category id are returned.
            If the category is a priamry, parent_category_id is None.

        Raises
        ------
            RepositoryError: If something went wrong with the database
        """
