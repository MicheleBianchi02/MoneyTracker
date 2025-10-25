import sqlite3

from moneytracker.core.domain.category import CategoryIn, CategoryOut
from moneytracker.core.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    ForeignKeyError,
    InvalidParameterError,
    RepositoryError,
)


class CategoryRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

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

        if not isinstance(cat_list, list):
            # Need this because if only a category is passed (not a list), in the
            # for we would get an error since Category is not an iteratable.
            cat_list = [cat_list]

        cursor = self._connection.cursor()

        sql = """
        INSERT INTO categories 
            (id_user,
            category_year,
            name,
            parent_category_id,
            category_type)
        VALUES 
            (?, ?, ?, ?, ?)
        """

        try:
            for cat in cat_list:
                # First we need to check if the primary is already present in the
                # database
                id_prim = self.get_id(
                    id_user,
                    cat.year,
                    cat.category_type,
                    cat.primary,
                    None,
                )

                # This will raise an error only if trying to add a primary. Because,
                # if a secondary is provided, the primary is ignored, if already present
                if id_prim is not None and cat.secondary is None:
                    raise DuplicateEntityError("Primary already present in the database")

                if id_prim is None:
                    # add primary if not exist in the database
                    parameters = (
                        id_user,
                        cat.year,
                        cat.primary,
                        None,
                        cat.category_type,
                    )

                    cursor.execute(sql, parameters)

                    id_prim = cursor.lastrowid

                if cat.secondary is not None:
                    if cat.category_type == "income":
                        raise InvalidParameterError("income can't have secondaries.")

                    id_sec = self.get_id(
                        id_user,
                        cat.year,
                        cat.category_type,
                        cat.primary,
                        cat.secondary,
                    )

                    if id_sec is None:
                        # add secondary
                        parameters = (
                            id_user,
                            cat.year,
                            cat.secondary,
                            id_prim,
                            cat.category_type,
                        )

                    # add secondary
                    parameters = (
                        id_user,
                        cat.year,
                        cat.secondary,
                        id_prim,
                        cat.category_type,
                    )

                    cursor.execute(sql, parameters)

            cursor.close()

        except sqlite3.DatabaseError as e:
            if "FOREIGN KEY constraint failed" in str(e):
                raise ForeignKeyError("Foreign key error") from e
            elif "UNIQUE constraint failed" in str(e):
                raise DuplicateEntityError("Unique constrainnt error") from e
            elif "CHECK constraint failed" in str(e):
                raise InvalidParameterError("Wrong category type inserted") from e

            raise RepositoryError("Error while adding category.") from e

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

        # Primary are the one with no parent. i.e. parent_category_id is null in the db

        cursor = self._connection.cursor()

        sql = """
            SELECT
                id_category,
                id_user,
                category_year,
                name,
                parent_category_id,
                category_type
            FROM 
                categories
            WHERE 
                id_user = ? AND parent_category_id IS NULL 
            """

        parameters = [id_user]

        if year is not None:
            sql += " AND category_year = ?"
            parameters.append(year)

        if cat_type is not None:
            sql += " AND category_type = ?"
            parameters.append(cat_type)

        parameters = tuple(parameters)

        try:
            cat_list = []

            cursor.execute(sql, parameters)
            ret_list = cursor.fetchall()

            for ret_cat in ret_list:
                cat = CategoryOut(
                    id_primary=ret_cat[0],
                    id_secondary=None,
                    id_user=ret_cat[1],
                    year=ret_cat[2],
                    primary=ret_cat[3],
                    secondary=None,
                    category_type=ret_cat[5],
                )

                cat_list.append(cat)

            cursor.close()
            return cat_list

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                "Error while getting primary categories for: "
                f"id_user:{id_user}, "
                f"year:{year}, "
                f"cat_type:{cat_type}. "
            ) from e

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

        # In this case cat_type is not needed since income doesn't have secondary

        cursor = self._connection.cursor()

        sql = """
            SELECT
                s.id_category,
                s.id_user,
                s.category_year,
                s.name,
                s.parent_category_id,
                s.category_type,
                p.name  -- primary name
            FROM
                categories s   -- 's' represents the secondary categories
            INNER JOIN         -- 'p' represents their primary parent
                categories p ON s.parent_category_id = p.id_category 
            WHERE
                s.id_user = ? 
                AND p.parent_category_id IS NULL
            """

        parameters = [id_user]

        if primary is not None:
            sql += "AND p.name = ?"
            parameters.append(primary)

        if year is not None:
            sql += "AND s.category_year = ?"
            parameters.append(year)

        parameters = tuple(parameters)

        try:
            cat_list = []

            cursor.execute(sql, parameters)
            ret_list = cursor.fetchall()

            for ret_cat in ret_list:
                cat = CategoryOut(
                    id_primary=ret_cat[4],  # parent_category_id
                    id_secondary=ret_cat[0],
                    id_user=ret_cat[1],
                    year=ret_cat[2],
                    category_type=ret_cat[5],
                    primary=ret_cat[6],
                    secondary=ret_cat[3],
                )

                cat_list.append(cat)

            cursor.close()
            return cat_list

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                "Error while getting secondary categories for: "
                f"id_user:{id_user}, "
                f"year:{year}, "
                f"primary_name:{primary}. "
            ) from e

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

        cursor = self._connection.cursor()

        sql_prim_name = """
            SELECT
                name
            FROM 
                categories
            WHERE
                id_category = ?
        """

        parameters = (id_prim,)

        sql_sec_list = """
            SELECT
                id_category, 
                id_user,
                category_year,
                name, 
                category_type
            FROM 
                categories
            WHERE
                parent_category_id = ?
        """

        try:
            cursor.execute(sql_prim_name, parameters)
            prim_name = cursor.fetchone()

            if prim_name is None:
                raise EntityNotFoundError("category", f"id_prim:{id_prim}")

            prim_name = prim_name[0]

            cursor.execute(sql_sec_list, parameters)
            raw_sec_list = cursor.fetchall()

            sec_list = []
            for sec in raw_sec_list:
                sec_list.append(
                    CategoryOut(
                        id_primary=id_prim,
                        id_secondary=sec[0],
                        id_user=sec[1],
                        year=sec[2],
                        category_type=sec[4],
                        primary=prim_name,
                        secondary=sec[3],
                    )
                )

            return sec_list

        except sqlite3.DatabaseError:
            raise RepositoryError(
                f"Error while getting secondary categories for the given id_prim:{id_prim}"
            )

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

        cursor = self._connection.cursor()

        # join is needed to get the primary name

        # We use left join even the output is not correctly ordered. The output will
        # be different in case the category is a primary or a secondary. This is
        # considerend only in the output, not inside the query
        sql = """
        SELECT
            s.id_category,
            s.id_user,
            s.category_year,
            s.name,
            s.parent_category_id,
            s.category_type,
            p.name  -- primary name
        FROM
            categories s   -- 's' represents the secondary categories
        LEFT JOIN          -- 'p' represents their primary parent
            categories p ON s.parent_category_id = p.id_category 
        WHERE
            s.id_user = ? 
            AND p.parent_category_id IS NULL
        """
        parameters = [id_user]

        if year is not None:
            sql += " AND s.category_year = ?"
            parameters.append(year)

        if cat_type is not None:
            sql += "  AND s.category_type = ?"
            parameters.append(cat_type)

        parameters = tuple(parameters)

        try:
            cat_list = []

            cursor.execute(sql, parameters)
            ret_list = cursor.fetchall()

            for ret_cat in ret_list:
                if ret_cat[6] is None:
                    # It mean that ret_cat is a primary
                    primary = ret_cat[3]
                    secondary = None
                    id_primary = ret_cat[0]
                    id_secondary = None

                else:
                    # It mean that ret_cat is a secondary
                    primary = ret_cat[6]
                    secondary = ret_cat[3]
                    id_primary = ret_cat[4]
                    id_secondary = ret_cat[0]

                cat = CategoryOut(
                    id_primary=id_primary,
                    id_secondary=id_secondary,
                    id_user=ret_cat[1],
                    year=ret_cat[2],
                    category_type=ret_cat[5],
                    primary=primary,
                    secondary=secondary,
                )

                cat_list.append(cat)

            cursor.close()
            return cat_list

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                "Error while getting categories for: "
                f"id_user:{id_user}, "
                f"year:{year}, "
                f"cat_type:{cat_type}. "
            ) from e

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

        # cat_type is required because an income and an expense can have the same name

        cursor = self._connection.cursor()

        if secondary is not None:
            sql = """
            SELECT 
                cat.id_category
            FROM 
                categories cat
            INNER JOIN 
                categories parent ON cat.parent_category_id = parent.id_category
            WHERE 
                cat.id_user = ? AND cat.category_year = ? AND cat.category_type = ? 
                AND parent.name = ? AND cat.name = ?
            """

            parameters = (id_user, year, cat_type, primary, secondary)

        else:
            sql = """
            SELECT
                id_category
            FROM 
                categories
            WHERE
                id_user = ? AND category_year = ? AND category_type = ? AND name = ? 
                AND parent_category_id is NULL
            """

            parameters = (id_user, year, cat_type, primary)

        try:
            cursor.execute(sql, parameters)
            res = cursor.fetchone()

            cursor.close()
            if res is None:
                return None
            else:
                return res[0]

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                "Error while getting id for category with: "
                f"id_user:{id_user}, "
                f"year:{year}, "
                f"cat_type:{cat_type}, "
                f"primary_name:{primary}, "
                f"secondary_name:{secondary}, "
            ) from e

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

        cursor = self._connection.cursor()

        # category_type is not modifiable because if we change from expense to income
        # and that category is parent to some other category (parent_category_id =
        # id_category of the edited category, i.e. it is a primary and there are some
        # secondary relating to that primary) we would need to change all of their type.
        # The same is true for the year.

        sql = """
            UPDATE 
                categories
            SET 
                name = ?
            WHERE 
                id_category = ?
            """
        parameters = (new_name, id_cat)

        try:
            cursor.execute(sql, parameters)
            cursor.close()
        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                f"Error while editing category with: id_cat = {id_cat}, name = {new_name}. "
            ) from e

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

        cursor = self._connection.cursor()

        parameters = ()

        sql = """
            DELETE FROM 
                categories
            WHERE 
                id_category = ?
            """

        parameters = (id_cat,)  # need to be a tuple

        try:
            cursor.execute(sql, parameters)
            cursor.close()
        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                f"Error while deleting category with: id_cat = {id_cat}, ",
            ) from e

    def validate_id_cat(
        self,
        id_cat: int,
    ) -> tuple[int | None, int | None, int | None, str | None]:
        """Check if the provided category id is present
        in the database.

        Parameters
        ----------
            id_cat (int) : id of the category

        Returns
        -------
            A tuple containing values in the following order:
            - id_user (int);
            - category_year (int);
            - parent_category_id (int);
            - category_type (str).

            If a match with the given id is not found, all these parameters will
            be set to None.

        Raises
        ------
            RepositoryError: If something went wrong with the database
        """
        cursor = self._connection.cursor()

        sql = """
            SELECT
                id_user,
                category_year,
                parent_category_id,
                category_type
            FROM
                categories
            WHERE
                id_category = ?;
        """

        parameters = (id_cat,)

        try:
            cat_get = cursor.execute(sql, parameters).fetchone()
            cursor.close()

            if cat_get is None:
                return None, None, None, None

            id_user = cat_get[0]
            year = cat_get[1]
            id_prim = cat_get[2]
            cat_type = cat_get[3]

            return id_user, id_prim, year, cat_type

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                f"Error while validating category with: id_cat = {id_cat}, ",
            ) from e
