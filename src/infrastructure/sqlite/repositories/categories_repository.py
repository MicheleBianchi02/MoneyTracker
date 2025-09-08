import sqlite3

from src.core.domain.category import CategoryIn, CategoryOut
from src.core.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    ForeignKeyError,
    InvalidParameterError,
    RepositoryError,
)
from src.core.repositories.abstract_category_repository import AbstractCategoryRepository


class CategoryRepository(AbstractCategoryRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, id_user: int, cat_list: list[CategoryIn] | CategoryIn) -> None:
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
        cursor = self._connection.cursor()

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

    def validate_id_cat(self, id_cat: int) -> int | None:
        cursor = self._connection.cursor()

        sql = """
            SELECT 
                id_user
            FROM
                categories
            WHERE
                id_category = ?;
        """

        parameters = (id_cat,)

        cat_get = cursor.execute(sql, parameters).fetchone()
        cursor.close()

        if cat_get is None:
            return None

        return cat_get[0]
