import collections
import sqlite3
from datetime import date, timedelta

from core.domain.transaction import TransactionOut, TransactionRepoIn
from core.exceptions import (
    EntityNotFoundError,
    ForeignKeyError,
    InvalidParameterError,
    RepositoryError,
)
from core.repositories.abstract_transaction_repository import (
    AbstractTransactionRepository,
)
from infrastructure.sqlite.repositories.categories_repository import CategoryRepository

# Used ein the get_summary function to substitute the None keys. Because None
# can't be parsed as a valid json key
NONE_REPLACEMENT = "N/A"


class TransactionRepository(AbstractTransactionRepository):
    def __init__(self, connection: sqlite3.Connection, cat_repo: CategoryRepository) -> None:
        self._connection = connection
        self._cat_repo = cat_repo

    def add(self, tr_list: list[TransactionRepoIn]) -> None:
        cursor = self._connection.cursor()

        sql = """
        INSERT INTO transactions (
            id_user, 
            id_category,
            tr_date,
            name,
            tr_value,
            description,
            currency)
        VALUES 
            (?, ?, ?, ?, ?, ?, ?)
        """

        try:
            parameters = [
                (
                    tr.id_user,
                    tr.id_cat,
                    tr.tr_date.isoformat(),
                    tr.name,
                    tr.value,
                    tr.description,
                    tr.currency,
                )
                for tr in tr_list
            ]

            cursor.executemany(sql, parameters)

            cursor.close()

        except sqlite3.DatabaseError as e:
            if "FOREIGN KEY constraint failed" in e:
                raise ForeignKeyError("Foreign key error") from e

            raise RepositoryError("Database error while adding transactions") from e

    def get(
        self,
        id_user: int,
        begin_date: date | None,
        end_date: date | None,
        to_currency: str | None = None,
        tr_type: str | None = None,
        primary: str | None = None,
        secondary: str | None = None,
        order: str | None = None,
        order_dir: str = "ASC",
        limit: int | None = None,
        offset: int = 0,
        name: str | None = None,
    ) -> tuple[list[TransactionOut], bool]:
        if begin_date is None:
            begin_date = date(1, 1, 1)

        if end_date is None:
            end_date = date(9999, 12, 31)

        begin_date = begin_date.isoformat()
        end_date = end_date.isoformat()

        cursor = self._connection.cursor()

        if order_dir not in ["ASC", "DESC"]:
            raise InvalidParameterError(f"Invalid order direction:{order_dir}")

        if order is not None:
            if order == "name":
                order = f"tr.name {order_dir}"
            elif order == "currency":
                order = f"tr.currency {order_dir}, tr.tr_date {order_dir}"
            elif order == "date":
                order = f"tr.tr_date {order_dir}"
            elif order == "value":
                order = f"tr.tr_value {order_dir}"

            elif order == "primary":
                order = f"primary_name {order_dir}, secondary_name {order_dir}"
            elif order == "secondary":
                order = f"secondary_name {order_dir}, primary_name {order_dir}"
            else:
                raise InvalidParameterError(f"Invalid order name:{order}")

        # This query will work even if the transaction is an expense and it's
        # category is a primary.

        # When the id_category in a transaction refer to a primary, the first
        # category (the c table) will have, as name, the primary name (c.name).
        # Since the parent_category_id is NULL, the database will return, for all
        # the column of the p table a NULL value (in this case p.name) (because the
        # database can't find a matching value for the parent_category_id since
        # each NULL value is unique).
        # If the transaction's category is a secondary, the c column will refer to
        # it (c.name is the secondary name) and, p will be its primary (because
        # c.parent_category_id = p.id_category for that primary), which means that
        # p.name is the primary name.

        # : p.name = NULL     => primary = c.name, secondary = NULL
        # : p.name = not NULL => primary = p.name, secondary = c.name

        # Since we are getting both income and expenses that can have as category
        # a primary, we can't simply say p.name = ? because, in that case, p.name
        # is always NULL. For those transactions we need to check on c.name

        sql = """
        SELECT
            tr.id_tr,
            tr.id_user,
            tr.tr_date,
            tr.name,
            tr.tr_value,
            tr.description,
            tr.currency,
            c.category_type,
            CASE  
                WHEN p.name IS NULL THEN 
                    c.name
                ELSE 
                    p.name
                END AS primary_name,
            CASE  
                WHEN p.name IS NULL THEN 
                    NULL
                ELSE 
                    c.name
                END AS secondary_name
        FROM 
            transactions tr
        INNER JOIN
            categories c ON tr.id_category = c.id_category
        LEFT JOIN
            categories p ON c.parent_category_id = p.id_category
        WHERE 
            tr.id_user = ?
            AND tr.tr_date BETWEEN ? AND ? 
        """

        parameters = [id_user, begin_date, end_date]
        try:
            if tr_type is not None:
                sql += " AND c.category_type = ? "
                parameters.append(tr_type)
                if primary is not None:
                    sql += """
                        AND (
                            (p.name = ? AND c.parent_category_id IS NOT NULL) OR
                            (c.name = ? AND c.parent_category_id IS NULL)
                        )
                    """
                    parameters.append(primary)
                    parameters.append(primary)

                    if secondary is not None:
                        sql += """
                            AND (
                                (c.name = ? AND c.parent_category_id IS NOT NULL)
                            )
                        """

                        parameters.append(secondary)

            if name is not None:
                # % and _ are used by sqlite.
                name = name.replace("\\", "\\\\")
                name = name.replace("%", "\\%")
                name = name.replace("_", "\\_")

                name += "%"

                sql += " AND tr.name LIKE ? ESCAPE '\\'"
                parameters.append(name)

            if order is not None:
                sql += f" ORDER BY {order}"

            if limit is not None:
                sql += " LIMIT ? OFFSET ?"
                parameters.extend([limit, offset])

            parameters = tuple(parameters)

            cursor.execute(sql, parameters)
            tr_ret_list = cursor.fetchall()

            if to_currency is not None and tr_ret_list:
                actual_min_date_str = min(t[2] for t in tr_ret_list)
                actual_max_date_str = max(t[2] for t in tr_ret_list)

                filled_rates = _get_raw_exc_rate(cursor, actual_min_date_str, actual_max_date_str)

            tr_list = []
            is_valid = True
            for tr in tr_ret_list:
                tr_date_str = tr[2]
                tr_currency = tr[6]
                tr_value = tr[4]

                if to_currency is not None:
                    tr_value, is_tr_valid = _get_converted_value(
                        filled_rates, tr_date_str, tr_currency, tr_value, to_currency
                    )
                    # register only the first false
                    if is_valid and not is_tr_valid:
                        is_valid = False

                    tr_currency = to_currency

                tr_list.append(
                    TransactionOut(
                        id=tr[0],
                        id_user=tr[1],
                        primary=tr[8],
                        secondary=tr[9],
                        tr_type=tr[7],
                        tr_date=date.fromisoformat(tr_date_str),
                        name=tr[3],
                        value=tr_value,
                        description=tr[5],
                        currency=tr_currency,
                    )
                )

            cursor.close()
            return tr_list, is_valid

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                "Error while getting transactions: "
                f"id_user:{id_user}, "
                f"begin_date:{begin_date}, "
                f"end_date:{end_date}, "
                f"tr_type:{tr_type}, "
                f"primary_name:{primary}, "
                f"secondary_name:{secondary}."
            ) from e

    def get_summary(
        self,
        id_user: int,
        begin_date: date | None,
        end_date: date | None,
        tr_type: str,
        to_currency: str,
        primary: str | None = None,
        secondary: str | None = None,
    ) -> tuple[dict[str, dict[str, dict[str, float]]], bool]:
        cursor = self._connection.cursor()

        if begin_date is None:
            begin_date = date(1, 1, 1)

        if end_date is None:
            end_date = date(9999, 12, 31)

        begin_date = begin_date.isoformat()
        end_date = end_date.isoformat()

        # In order for this query to work, the exchange rate saved in the same date must
        # have all the same from_currency value (eg 'EUR').

        # See the comment in the get method for an explanation of the first case clause.

        try:
            # TODO: For better performance we can spawn two threads that can take
            # transactions and exchange rates indipendently. Maybe there are problem
            # with the connection (can't share connection with multiple thread)?
            # Maybe rewrite something in C? Or change the logic.
            cursor = self._connection.cursor()

            # Fetch all relevant raw transactions (same as before)
            sql_transactions = """
                SELECT
                    tr.tr_date, tr.currency, tr.tr_value,

                CASE
                    WHEN p.name IS NULL THEN c.name
                    ELSE p.name
                END AS primary_category,

                CASE
                    WHEN p.name IS NULL THEN NULL
                    ELSE c.name
                END AS secondary_category

                FROM transactions tr
                INNER JOIN categories c
                    ON tr.id_category = c.id_category
                LEFT JOIN categories p
                    ON c.parent_category_id = p.id_category
                WHERE
                    tr.id_user = ? AND
                    c.category_type = ? AND
                    tr.tr_date BETWEEN ? AND ?

                    AND (? IS NULL OR
                        (p.name = ? AND p.name IS NOT NULL) OR
                        (c.name = ? AND p.name IS NULL)
                    )
                    AND (? IS NULL OR
                        (c.name = ? AND p.name IS NOT NULL)
                    )
            """
            params_transactions = [
                id_user,
                tr_type,
                begin_date,
                end_date,
                primary,
                primary,
                primary,
                secondary,
                secondary,
            ]
            cursor.execute(sql_transactions, params_transactions)
            transactions = cursor.fetchall()

            if not transactions:
                return {}, True

            # Determine the actual min/max dates from the transactions found
            actual_min_date_str = min(t[0] for t in transactions)
            actual_max_date_str = max(t[0] for t in transactions)

            filled_rates = _get_raw_exc_rate(cursor, actual_min_date_str, actual_max_date_str)

            summary_data = {}
            is_valid = True

            for tr_date_str, tr_currency, tr_value, primary_cat, secondary_cat in transactions:
                month_year = tr_date_str[:7]  # yyyy-mm
                secondary_key = secondary_cat if secondary_cat is not None else NONE_REPLACEMENT

                converted_value, is_tr_valid = _get_converted_value(
                    filled_rates, tr_date_str, tr_currency, tr_value, to_currency
                )

                # register only the first false
                if is_valid and not is_tr_valid:
                    is_valid = False

                level1 = summary_data.setdefault(primary_cat, {})
                level2 = level1.setdefault(secondary_key, {})
                level2[month_year] = level2.get(month_year, 0.0) + converted_value

            cursor.close()
            return summary_data, is_valid

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                "Error while getting transactions summary for: "
                f"id_user:{id_user}, "
                f"begin_date:{begin_date}, "
                f"end_date:{end_date}, "
                f"tr_type:{tr_type}, "
                f"to_currency:{to_currency}, "
                f"primary:{primary}, "
                f"secondary:{secondary}. "
            ) from e

        return summary_data, is_valid

    def get_by_id_cat(self, id_cat: int) -> list[TransactionOut]:
        # Used by the category service when trying to delete a category.
        cursor = self._connection.cursor()

        # See the get method to understand the CASE statement
        sql = """
            SELECT
                tr.id_tr,
                tr.id_user,
                tr.tr_date,
                tr.name,
                tr.tr_value,
                tr.description,
                tr.currency,
                c.category_type,
                
                CASE  
                    WHEN p.name IS NULL THEN 
                        c.name
                    ELSE 
                        p.name
                    END AS primary_name,
                CASE  
                    WHEN p.name IS NULL THEN 
                        NULL
                    ELSE 
                        c.name
                    END AS secondary_name

            FROM 
                transactions tr
            INNER JOIN
                categories c ON tr.id_category = c.id_category
            LEFT JOIN
                categories p ON c.parent_category_id = p.id_category
            WHERE 
                tr.id_category = ?
        """

        parameters = (id_cat,)

        try:
            cursor.execute(sql, parameters)
            tr_ret_list = cursor.fetchall()

            tr_list = []

            for tr_ret in tr_ret_list:
                tr = TransactionOut(
                    id=tr_ret[0],
                    id_user=tr_ret[1],
                    primary=tr_ret[8],
                    secondary=tr_ret[9],
                    tr_type=tr_ret[7],
                    tr_date=date.fromisoformat(tr_ret[2]),
                    name=tr_ret[3],
                    value=tr_ret[4],
                    description=tr_ret[5],
                    currency=tr_ret[6],
                )

                tr_list.append(tr)

            cursor.close()
            return tr_list

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                f"Error while getting transactions with category id: {id_cat}"
            ) from e

    def edit(self, id_tr: int, new_tr: TransactionRepoIn) -> None:
        cursor = self._connection.cursor()

        sql = """
            UPDATE 
                transactions
            SET
                id_category = ?,
                tr_date = ?,
                name = ?,
                tr_value = ?,
                description = ?,
                currency = ?
            WHERE
                id_tr = ?
            """

        parameters = (
            new_tr.id_cat,
            new_tr.tr_date.isoformat(),
            new_tr.name,
            new_tr.value,
            new_tr.description,
            new_tr.currency,
            id_tr,
        )

        try:
            cursor.execute(sql, parameters)
            cursor.close()

        except sqlite3.DatabaseError as e:
            if "FOREIGN KEY constraint failed" in e:
                # when the new id_cat is not present
                raise ForeignKeyError("Foreign key error") from e

            raise RepositoryError(
                f"Database failed while editing transaction: id_tr:{id_tr}, new_tr:{new_tr}. "
            ) from e

    def delete(self, id_tr: int) -> None:
        cursor = self._connection.cursor()
        sql = """
            DELETE FROM
                transactions
            WHERE
                id_tr = ?
            """
        parameter = (id_tr,)

        try:
            cursor.execute(sql, parameter)
            cursor.close()

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                f"Database failed while deleting transaction: id_tr:{id_tr}. "
            ) from e

    def get_by_id_tr(self, id_tr: int) -> TransactionOut | None:
        cursor = self._connection.cursor()

        # See the get method to understand the CASE block below
        sql = """
        SELECT
            tr.id_tr,
            tr.id_user,
            tr.tr_date,
            tr.name,
            tr.tr_value,
            tr.description,
            tr.currency,
            c.category_type,
            CASE  
                WHEN p.name IS NULL THEN 
                    c.name
                ELSE 
                    p.name
                END AS primary_name,
            CASE  
                WHEN p.name IS NULL THEN 
                    NULL
                ELSE 
                    c.name
                END AS secondary_name
        FROM 
            transactions tr
        INNER JOIN
            categories c ON tr.id_category = c.id_category
        LEFT JOIN
            categories p ON c.parent_category_id = p.id_category
        WHERE 
            tr.id_tr = ?
        """

        parameters = (id_tr,)

        try:
            cursor.execute(sql, parameters)
            tr_get = cursor.fetchone()

            if tr_get is None:
                return None

            return TransactionOut(
                id=tr_get[0],
                id_user=tr_get[1],
                primary=tr_get[8],
                secondary=tr_get[9],
                tr_type=tr_get[7],
                tr_date=date.fromisoformat(tr_get[2]),
                name=tr_get[3],
                value=tr_get[4],
                currency=tr_get[6],
                description=tr_get[7],
            )

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                f"Database failed while getting transaction with id_tr:{id_tr}. "
            ) from e


def _get_raw_exc_rate(cursor: sqlite3.Cursor, begin_date: str, end_date: str) -> dict:
    """Get all exchange rate in the given date range."""
    # TODO: Instead of fetching all currencies, get all exchange rate with the
    # exchange rate for the transaction currencies and for the given to_currency

    # Fetch all exchange rates within the actual transaction date range
    sql_rates = """
        SELECT
            rate_date,
            from_currency,
            to_currency,
            rate,
            is_updated
        FROM
            exchange_rates
        WHERE
            rate_date BETWEEN ? AND ?
    """
    cursor.execute(sql_rates, [begin_date, end_date])
    rates_raw = cursor.fetchall()

    # Create a rate "lookup" map, now storing the original rate date
    rates_map = collections.defaultdict(dict)
    for r_date, r_from, r_to, r_rate, r_is_updated in rates_raw:
        rates_map[r_date][r_to] = {
            "rate": r_rate,
            "from": r_from,
            "date": r_date,
            "is_updated": True if r_is_updated == 1 else False,
        }

    # When a transaction is added to the db, first it is checked that the
    # exchange rates is present in the database if the date is less than a
    # given starting date (see transaction service). For transactions
    # with date bigger than that, the exchange rate is not added to the db (if
    # not already present). So, for those dates, we need to use the last
    # available date in the database.

    # Forward-fill logic to handle gaps (i.e. missing exchange rates)
    filled_rates = {}
    last_known_rates = {}
    current_date = date.fromisoformat(begin_date)
    end_date_obj = date.fromisoformat(end_date)
    while current_date <= end_date_obj:
        current_date_str = current_date.isoformat()
        if current_date_str in rates_map:  # in keys
            # Update last known rates with any new rates from today
            # Need to clear each time because if the from_currency parameter
            # changes between dates, we will get an error.
            last_known_rates.clear()
            for currency, rate_info in rates_map[current_date_str].items():
                last_known_rates[currency] = rate_info

        filled_rates[current_date_str] = last_known_rates.copy()
        current_date += timedelta(days=1)

    return filled_rates


def _get_converted_value(
    filled_rates: dict,
    tr_date_str: str,
    tr_currency: str,
    tr_value: float,
    to_currency: str,
) -> tuple[float, bool]:
    """Get the converted value.

    Return the converted value based on the provided to_currency. Return also
    if the exchange rate used is updated and with the same date.
    """
    is_valid = True
    converted_value = 0

    if tr_currency == to_currency:
        converted_value = tr_value
    else:
        rates_for_day = filled_rates.get(tr_date_str)
        if not rates_for_day:
            raise EntityNotFoundError(
                "exchange rate",
                f"tr_date:{tr_date_str}",
            )

        # All exchange rates of the same date must have the same
        # from_currency parameter.
        base_currency_candidates = {info["from"] for info in rates_for_day.values()}
        if not base_currency_candidates:
            raise EntityNotFoundError("exchange rate-base_currency", f"tr_date:{tr_date_str}")
        base_currency = base_currency_candidates.pop()  # e.g. EUR

        if to_currency == base_currency:
            # Case 1: Convert TO the base currency (e.g., CNY -> EUR).
            rate_to_base_info = rates_for_day.get(tr_currency)
            if not rate_to_base_info:
                raise EntityNotFoundError(
                    "exchange rate",
                    f"conversion:{tr_currency}->{base_currency}, tr_date:{tr_date_str}",
                )
            converted_value = tr_value / rate_to_base_info["rate"]
            if rate_to_base_info["date"] != tr_date_str or not rate_to_base_info["is_updated"]:
                is_valid = False

        elif tr_currency == base_currency:
            # Case 2: Convert FROM the base currency (e.g., EUR -> USD).
            rate_from_base_info = rates_for_day.get(to_currency)
            if not rate_from_base_info:
                raise EntityNotFoundError(
                    "exchange rate",
                    f"conversion:{base_currency}->{to_currency}, tr_date:{tr_date_str}",
                )

            converted_value = tr_value * rate_from_base_info["rate"]

            if rate_from_base_info["date"] != tr_date_str or not rate_from_base_info["is_updated"]:
                is_valid = False

        else:
            # Case 3: Three-way conversion (e.g., CNY -> EUR -> USD).
            rate_to_base_info = rates_for_day.get(tr_currency)
            rate_from_base_info = rates_for_day.get(to_currency)
            if not rate_to_base_info or not rate_from_base_info:
                raise EntityNotFoundError(
                    "exchange rate",
                    f"conversion:{tr_currency}->{base_currency}->{to_currency}, "
                    f"tr_date:{tr_date_str}",
                )

            converted_value = (tr_value / rate_to_base_info["rate"]) * rate_from_base_info["rate"]
            if (
                rate_to_base_info["date"] != tr_date_str
                or rate_from_base_info["date"] != tr_date_str
                or not rate_to_base_info["is_updated"]
                or not rate_from_base_info["is_updated"]
            ):
                is_valid = False

    return converted_value, is_valid
