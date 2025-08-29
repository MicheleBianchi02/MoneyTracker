import collections
import sqlite3
from datetime import date, timedelta

from src.core.domain.transaction import TransactionIn, TransactionOut
from src.core.exceptions import EntityNotFoundError, ForeignKeyError, RepositoryError
from src.core.repositories.abstract_transaction_repository import (
    AbstractTransactionRepository,
)
from src.infrastructure.sqlite.repositories.categories_repository import CategoryRepository


class TransactionRepository(AbstractTransactionRepository):
    def __init__(self, connection: sqlite3.Connection, cat_repo: CategoryRepository) -> None:
        self._connection = connection
        self._cat_repo = cat_repo

    def add(self, transaction_list: list[TransactionIn] | TransactionIn) -> None:
        if not isinstance(transaction_list, list):
            # Need this because if only a Transaction is passed (not a list), in the
            # for we would get an error since Transaction is not an iteratable.
            transaction_list = [transaction_list]

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
            for tr in transaction_list:
                id_user = tr.id_user
                tr_date = tr.tr_date
                primary_name = tr.primary
                secondary_name = tr.secondary
                tr_type = tr.tr_type

                id_category = self._cat_repo.get_id(
                    id_user,
                    tr_date.year,
                    tr_type,
                    primary_name,
                    secondary_name,
                )

                if id_category is None:
                    raise EntityNotFoundError(
                        "category",
                        f"id_user:{id_user}, "
                        f"tr_year:{tr_date.year}, "
                        f"tr_type:{tr_type}, "
                        f"primary_name:{primary_name}, "
                        f"secondary_name:{secondary_name}. ",
                    )

                parameters = (
                    id_user,
                    id_category,
                    tr_date.isoformat(),
                    tr.name,
                    tr.value,
                    tr.description,
                    tr.currency,
                )

                cursor.execute(sql, parameters)

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
        tr_type: str | None = None,
        primary: str | None = None,
        secondary: str | None = None,
    ) -> list[TransactionOut]:
        # TODO:
        # * Pagination: Don't fetch thousands of rows at once.
        # Modify the get method to accept limit and offset parameters and use them in the query.
        # Also add some way to order the data. Like an argument that can be the column
        # on which ordering the returned values. Also add the direction (ASC or DES).
        # Need when the table displaying the data require an ordered column.

        # TODO: Add a way to search for transactions by their name. The entire name
        # should not be needed, just the beginning. Use LIKE
        #     * Implement Full-Text Search for Transactions (`transaction_repository.py`): A simple LIKE search on transaction names or descriptions will become slow as the database grows.
        # * Suggestion: Use SQLite's FTS5 extension. Create a virtual table like CREATE VIRTUAL TABLE transactions_fts USING fts5(name, description, content='transactions',
        #   content_rowid='id_tr');. You would then set up triggers to automatically keep this FTS table in sync with your transactions table. Your search queries would then be directed at the
        #   transactions_fts table, which is incredibly fast and supports complex queries (e.g., NEAR, AND, OR).

        # # In TransactionRepository.get() signature
        # def get(self, ..., limit: int = 100, offset: int = 0) -> list[TransactionOut]:
        #     # ...
        #     sql += " LIMIT ? OFFSET ?"
        #     parameters.extend([limit, offset])
        #     # ...

        if begin_date is None:
            begin_date = date(1, 1, 1)

        if end_date is None:
            end_date = date(9999, 12, 31)

        begin_date = begin_date.isoformat()
        end_date = end_date.isoformat()

        cursor = self._connection.cursor()

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
            AND tr_date BETWEEN ? AND ? 
        """

        parameters = [id_user, begin_date, end_date]
        if tr_type is not None:
            sql += "AND c.category_type = ? "
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

        parameters = tuple(parameters)

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

        # Consider a from_currency = 'EUR' for all exchange rates.
        # Say we want to convert all the transactions to 'USD'.

        # There are different cases that can occour:
        # 1) tr.currency = 'USD'
        # In this case no transformation is needed => value is simply tr.value

        # 2) tr.currency = 'EUR' (i.e. == from_currency column)
        # the resulting value is tr.value * Rate(EUR->USD)

        # 3) tr.currency = 'CAD'  (i.e. != 'EUR' and != 'USD')
        # the resulting value should be tr.value / Rate(EUR->CAD) * Rate(EUR->USD)
        # in that case we have that tr.currency is equal to the to_currency column
        # of the exchange rate's table.

        # 4) If the currency to convert into is the from_currency (ie 'EUR') the
        # resulting value is tr.value / Rate(EUR->tr.currency)

        # To obtain those value we can perform two LEFT JOIN on the exchange table
        # One requiring that tr.currency = to_currency and the second one with
        # to_currency = 'USD' (or ?)

        # In the first and second case the first join will return a NULL column

        # In the third case we have that tr.currency is the same of a row in the to_currency
        # column of the first join. Meaning that both join will not result in a NULL column

        # In the forth case the first join give a NULL column, the second join will
        # result in the correct value (not NULL)

        # The first table of the join takes the name of exc_to because we are joining
        # on the to_currency column and is used when tr.currency = exc_to.to_currency
        # and when tr.currency = exc_to.from_currency.
        # The exchange rate's table used in the second join is called exc_f because it's
        # used when converting from the from_currency to the final currency (the required
        # one).

        # If some exchange rate are not present in the database we may sum NULL values
        # (when entering the ELSE statement). In this case the SUM function will simply
        # ignore these values producing wrong results. The last CASE statement with the
        # COUNT clause check if all exchange rate needed for the conversion are present
        # in the database. If not 0 is returned. We don't check that all the exchange
        # rates are present in the database but that only the required one are present.
        # i.e. if for all transactions tr.currency = ? the has_null column will be 1 even
        # if the exchange rate table is empty.

        # sql = """
        # WITH transactions_with_rates AS (
        #     SELECT
        #         tr.tr_value,
        #         tr.currency,
        #         tr.tr_date,
        #
        #         CASE
        #             WHEN p.name IS NULL THEN c.name
        #             ELSE p.name
        #         END AS primary_category,
        #
        #         CASE
        #             WHEN p.name IS NULL THEN NULL
        #             ELSE c.name
        #         END AS secondary_category,
        #
        #
        #         exc_to.from_currency AS base_currency,
        #         exc_to.rate AS rate_to_base,
        #         exc_to.rate_date AS date_to_base,
        #         exc_f.rate AS rate_from_base,
        #         exc_f.rate_date AS date_from_base
        #
        #     FROM
        #         transactions tr
        #     INNER JOIN
        #         categories c ON tr.id_category = c.id_category
        #     LEFT JOIN
        #         categories p ON c.parent_category_id = p.id_category
        #
        #     -- For each transaction, find the single best "to_base" exchange rate record.
        #     LEFT JOIN LATERAL (
        #         SELECT from_currency, rate, rate_date FROM exchange_rates
        #         WHERE to_currency = tr.currency AND rate_date <= tr.tr_date
        #         ORDER BY rate_date DESC LIMIT 1
        #     ) AS exc_to
        #
        #     -- For each transaction, find the single best "from_base" exchange rate record.
        #     LEFT JOIN LATERAL (
        #         SELECT rate, rate_date FROM exchange_rates
        #         WHERE to_currency = ? AND rate_date <= tr.tr_date
        #         ORDER BY rate_date DESC LIMIT 1
        #     ) AS exc_f
        #
        #     WHERE
        #         tr.id_user = ?
        #         AND c.category_type = ?
        #         AND tr.tr_date BETWEEN ? AND ?
        #
        #         -- For primary name
        #         AND (? IS NULL OR
        #             (p.name = ? AND c.parent_category_id IS NOT NULL) OR
        #             (c.name = ? AND c.parent_category_id IS NULL)
        #         )
        #
        #         -- For secondary name
        #         AND (? IS NULL OR
        #             (c.name = ? AND c.parent_category_id IS NOT NULL)
        #         )
        # )
        #
        # SELECT
        #     t.primary_category,
        #     t.secondary_category,
        #
        #     strftime('%Y-%m', t.tr_date) AS month_year,
        #
        #     -- Calculate the total value, converting currencies as needed.
        #     SUM (
        #         CASE
        #             -- 1. Transaction is already in the target currency.
        #             WHEN t.currency = ? THEN t.tr_value
        #
        #             -- 2: Direct conversion from base currency to target (e.g. EUR -> USD).
        #             WHEN t.currency = t.base_currency
        #                 THEN t.tr_value * t.rate_from_base
        #
        #             -- 3: Indirect conversion (e.g., CAD -> EUR -> USD). Both rates must exist.
        #             WHEN t.rate_to_base IS NOT NULL AND t.rate_from_base IS NOT NULL
        #                 THEN (t.tr_value / t.rate_to_base) * t.rate_from_base
        #
        #             -- 4: Conversion TO the base currency (e.g., CAD -> EUR).
        #             -- This happens when the target currency IS the base currency.
        #             WHEN t.base_currency = ?
        #                 THEN t.tr_value / t.rate_from_base
        #
        #             -- If none of the above conditions are met, the conversion is impossible.
        #             -- e.g. when the exchange rate doesn't exist in the db.
        #             ELSE NULL
        #         END
        #     ) AS total_value,
        #
        #     -- Check if all rates used are correct (i.e. have the same date as the
        #     -- transaction)
        #     MIN(
        #         CASE
        #             -- If no conversion is needed, it's always current.
        #             WHEN t.currency = ? THEN 1
        #             -- If converting from base, check the date of the 'from_base' rate.
        #             WHEN t.currency = t.base_currency
        #                 THEN IIF(t.tr_date = t.date_from_base, 1, 0)
        #             -- If converting to base, check the date of the 'to_base' rate.
        #             WHEN ? = t.base_currency
        #                 THEN IIF(t.tr_date = t.date_to_base, 1, 0)
        #             -- For 3-way conversion, both dates must match the transaction date.
        #             ELSE IIF(t.tr_date = t.date_to_base AND t.tr_date = t.date_from_base, 1, 0)
        #         END
        #     ) AS all_rates_are_current,
        #
        #     -- SUM skip NULL values. This check that all the summed values are not NULL.
        #     -- i.e. all the required exchange_rates are present in the database.
        #     CASE
        #         WHEN COUNT(*) != COUNT(
        #             CASE
        #                 WHEN t.currency = ? THEN 1
        #                 WHEN t.currency = t.base_currency AND t.rate_from_base IS NOT NULL THEN 1
        #                 WHEN t.currency != t.base_currency AND ? != t.base_currency
        #                     AND t.rate_to_base IS NOT NULL AND t.rate_from_base IS NOT NULL THEN 1
        #                 WHEN ? = t.base_currency AND t.rate_to_base IS NOT NULL THEN 1
        #                 ELSE NULL
        #             END
        #         ) THEN 1
        #         ELSE 0
        #     END AS has_null
        #
        #     FROM
        #         transactions_with_rates t
        #     GROUP BY
        #         t.primary_category, t.secondary_category, month_year
        #     ORDER BY
        #         t.primary_category, t.secondary_category, month_year;
        # """
        #
        # parameters = [
        #     to_currency,  # second lateral join
        #     id_user,
        #     tr_type,
        #     begin_date,
        #     end_date,
        #     primary,
        #     primary,
        #     primary,
        #     secondary,
        #     secondary,
        #     to_currency,  # for SUM(CASE)
        #     to_currency,  # for SUM(CASE)
        #     to_currency,  # for MIN(CASE)
        #     to_currency,  # for MIN(CASE)
        #     to_currency,  # for COUNT(CASE)
        #     to_currency,  # for COUNT(CASE)
        #     to_currency,  # for COUNT(CASE)
        # ]

        sql = """
        WITH transactions_with_rates AS (
            SELECT
                tr.tr_value,
                tr.currency,
                tr.tr_date,
                CASE WHEN p.name IS NULL THEN c.name ELSE p.name END AS primary_category,
                CASE WHEN p.name IS NULL THEN NULL ELSE c.name END AS secondary_category,

                (SELECT from_currency FROM exchange_rates
                    WHERE rate_date <= tr.tr_date 
                    ORDER BY rate_date DESC LIMIT 1) AS base_currency,
                
                (SELECT rate FROM exchange_rates 
                WHERE to_currency = tr.currency AND rate_date <= tr.tr_date 
                ORDER BY rate_date DESC LIMIT 1) AS rate_to_base,

                (SELECT rate_date FROM exchange_rates 
                WHERE to_currency = tr.currency AND rate_date <= tr.tr_date 
                ORDER BY rate_date DESC LIMIT 1) AS date_to_base,

                (SELECT rate FROM exchange_rates 
                WHERE to_currency = ? AND rate_date <= tr.tr_date 
                ORDER BY rate_date DESC LIMIT 1) AS rate_from_base,

                (SELECT rate_date FROM exchange_rates 
                WHERE to_currency = ? AND rate_date <= tr.tr_date 
                ORDER BY rate_date DESC LIMIT 1) AS date_from_base

            FROM
                transactions tr
            INNER JOIN
                categories c ON tr.id_category = c.id_category
            LEFT JOIN
                categories p ON c.parent_category_id = p.id_category
            WHERE
                tr.id_user = ?
                AND c.category_type = ?
                AND tr.tr_date BETWEEN ? AND ?
                AND (? IS NULL OR
                     (p.name = ? AND c.parent_category_id IS NOT NULL) OR
                     (c.name = ? AND c.parent_category_id IS NULL))
                AND (? IS NULL OR
                     (c.name = ? AND c.parent_category_id IS NOT NULL))
        )
        SELECT
            t.primary_category,
            t.secondary_category,
            strftime('%Y-%m', t.tr_date) AS month_year,

            SUM(
                CASE
                    WHEN t.currency = ? THEN t.tr_value
                    WHEN t.currency = t.base_currency THEN t.tr_value * t.rate_from_base
                    WHEN t.rate_to_base IS NOT NULL AND t.rate_from_base IS NOT NULL 
                        THEN (t.tr_value / t.rate_to_base) * t.rate_from_base
                    WHEN ? = t.base_currency THEN t.tr_value / t.rate_to_base
                    ELSE NULL
                END
            ) AS total_value,

            MIN(
                CASE
                    WHEN t.currency = ? THEN 1
                    WHEN t.currency = t.base_currency THEN IIF(t.tr_date = t.date_from_base, 1, 0)
                    WHEN ? = t.base_currency THEN IIF(t.tr_date = t.date_to_base, 1, 0)
                    ELSE IIF(t.tr_date = t.date_to_base AND t.tr_date = t.date_from_base, 1, 0)
                END
            ) AS all_rates_are_current,

            CASE
                WHEN COUNT(*) != COUNT(
                    CASE
                        WHEN t.currency = ? THEN 1
                        WHEN t.currency = t.base_currency AND t.rate_from_base IS NOT NULL THEN 1
                        WHEN t.currency != t.base_currency AND ? != t.base_currency AND t.rate_to_base IS NOT NULL AND t.rate_from_base IS NOT NULL THEN 1
                        WHEN ? = t.base_currency AND t.rate_to_base IS NOT NULL THEN 1
                        ELSE NULL
                    END
                ) THEN 1
                ELSE 0
            END AS has_null
        FROM
            transactions_with_rates t
        GROUP BY
            t.primary_category, t.secondary_category, month_year
        ORDER BY
            t.primary_category, t.secondary_category, month_year;
        """

        parameters = [
            # For subqueries in CTE
            to_currency,
            to_currency,
            # For WHERE clause in CTE
            id_user,
            tr_type,
            begin_date,
            end_date,
            primary,
            primary,
            primary,
            secondary,
            secondary,
            # For main SELECT statement
            to_currency,  # SUM
            to_currency,  # SUM
            to_currency,  # MIN
            to_currency,  # MIN
            to_currency,  # has_null
            to_currency,  # has_null
            to_currency,  # has_null
        ]

        try:
            # TODO: None can't be used as keys in json. Change to something else

            # cursor.execute(sql, parameters)
            # results = cursor.fetchall()
            #
            # is_valid = True  # if the resulting values are correct
            # summary_data = {}
            # # The query returns 5 columns: primary, secondary, month_year, total, is_updated
            # for primary_cat, secondary_cat, month_year, total, all_current, has_null in results:
            #     secondary_key = secondary_cat if secondary_cat is not None else "N/A"
            #
            #     # Set up nested dictionaries
            #     level1 = summary_data.setdefault(primary_cat, {})
            #     level2 = level1.setdefault(secondary_key, {})
            #
            #     if has_null == 1:
            #         raise EntityNotFoundError("exchange rate", f"date:{month_year}")
            #
            #     # Populate the data for the month
            #     level2[month_year] = total
            #
            #     # all_current is 1 when all the used exchange rates had the same date
            #     # as the transaction. For example, if a transaction's date is in the
            #     # future this parameter, for that month, will be 1.
            #     if all_current == 0:
            #         is_valid = False
            #
            # return summary_data, is_valid
            #

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
            cursor.execute(sql_rates, [actual_min_date_str, actual_max_date_str])
            rates_raw = cursor.fetchall()

            # Create an efficient rate "lookup" map, now storing the original rate date
            rates_map = collections.defaultdict(dict)
            for r_date, r_from, r_to, r_rate, r_is_updated in rates_raw:
                rates_map[r_date][r_to] = {
                    "rate": r_rate,
                    "from": r_from,
                    "date": r_date,
                    "is_updated": True if r_is_updated == 1 else False,
                }

            # Forward-fill logic to handle gaps (i.e. missing exchange rates)
            filled_rates = {}
            last_known_rates = {}
            current_date = date.fromisoformat(actual_min_date_str)
            end_date_obj = date.fromisoformat(actual_max_date_str)
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

            summary_data = {}
            is_valid = True  # Start by assuming all rates are current

            for tr_date_str, tr_currency, tr_value, primary_cat, secondary_cat in transactions:
                month_year = tr_date_str[:7]  # yyyy-mm
                secondary_key = secondary_cat if secondary_cat is not None else "N/A"

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
                        raise EntityNotFoundError(
                            "exchange rate-base_currency", f"tr_date:{tr_date_str}"
                        )
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
                        if (
                            rate_to_base_info["date"] != tr_date_str
                            or not rate_to_base_info["is_updated"]
                        ):
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

                        if (
                            rate_from_base_info["date"] != tr_date_str
                            or not rate_from_base_info["is_updated"]
                        ):
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

                        converted_value = (
                            tr_value / rate_to_base_info["rate"]
                        ) * rate_from_base_info["rate"]
                        if (
                            rate_to_base_info["date"] != tr_date_str
                            or rate_from_base_info["date"] != tr_date_str
                            or not rate_to_base_info["is_updated"]
                            or not rate_from_base_info["is_updated"]
                        ):
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

    def edit(self, id_tr: int, new_tr: TransactionIn) -> None:
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

        # raise exception if transaction doesn't exist in the db
        self._validate_edit_delete(id_tr)

        id_user = new_tr.id_user
        tr_date = new_tr.tr_date
        primary_name = new_tr.primary
        secondary_name = new_tr.secondary
        tr_type = new_tr.tr_type

        id_category = self._cat_repo.get_id(
            id_user,
            tr_date.year,
            tr_type,
            primary_name,
            secondary_name,
        )

        if id_category is None:
            raise EntityNotFoundError(
                "category",
                f"id_user:{id_user}, tr_year:{tr_date.year}, tr_type:{tr_type}, "
                f"primary_name:{primary_name}, secondary_name:{secondary_name}",
            )

        parameters = (
            id_category,
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

        self._validate_edit_delete(id_tr)

        try:
            cursor.execute(sql, parameter)
            cursor.close()

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                f"Database failed while deleting transaction: id_tr:{id_tr}. "
            ) from e

    def _validate_edit_delete(self, id_tr: int) -> None:
        """Check if the transaction with the given id exist in the db.

        If nothing is found an EntityNotFoundError is raised.
        """

        cursor = self._connection.cursor()

        sql = """
            SELECT 1
            FROM
                transactions
            WHERE
                id_tr = ?;
        """

        parameters = (id_tr,)

        tr_get = cursor.execute(sql, parameters).fetchone()
        cursor.close()
        if tr_get is None:
            raise EntityNotFoundError("transaction", f"id_tr:{id_tr}")
