import sqlite3

from src import default_settings


def initialize_database(connection: sqlite3.Connection) -> None:
    try:
        _init_user(connection)

        _init_categories(connection)

        _init_exchange_rate(connection)

        _init_transactions(connection)

        _init_user_settings(connection)

        _init_app_config(connection)

    except sqlite3.DatabaseError as e:
        raise RuntimeError(f"Error while initializing the database: {str(e)}") from e


def _init_user(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS
            users(
                id_user INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT
            ) STRICT
        """
    )

    cursor.close()


def _init_exchange_rate(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exchange_rates (
            from_currency TEXT NOT NULL,
            to_currency TEXT NOT NULL,
            rate REAL,
            rate_date TEXT NOT NULL, -- Use 'YYYY-MM-DD' format
            is_updated INTEGER,
            CHECK (from_currency <> to_currency)
            UNIQUE (from_currency, to_currency, rate_date)
        ) STRICT
       """)

    cursor.execute("""
       CREATE INDEX IF NOT EXISTS
           idx_exr_date_to_currency
       ON
           exchange_rates(rate_date, to_currency)
       """)

    cursor.close()


def _init_categories(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()
    # Create category table

    # Example:
    # +-------------+---------+---------------+-----------+--------------------+---------------+
    # | id_category | id_user | category_year | name      | parent_category_id | category_type |
    # +-------------+---------+---------------+-----------+--------------------+---------------+
    # | 5           | 123     | 2025          | Transport | NULL               | expense       |
    # +-------------+---------+---------------+-----------+--------------------+---------------+
    # | 6           | 123     | 2025          | Gas       | 5                  | expense       |
    # +-------------+---------+---------------+-----------+--------------------+---------------+
    # | 7           | 123     | 2025          | Train     | 5                  | expense       |
    # +-------------+---------+---------------+-----------+--------------------+---------------+
    # | 8           | 123     | 2025          | Cinema    | 2                  | expense       |
    # +-------------+---------+---------------+-----------+--------------------+---------------+
    # | 9           | 123     | 2025          | Salary    | NULL               | income        |
    # +-------------+---------+---------------+-----------+--------------------+---------------+
    # | 10          | 123     | 2025          | Trip      | NULL               | expense       |
    # +-------------+---------+---------------+-----------+--------------------+---------------+

    # the one with id_category = 5 (Transport) is a primary. The secondaries
    # relative to that primary are 6 and 7 (Gas and Train)

    # We can use ON DELETE RESTRICT such that it is impossible to delete a primary if
    # it is parent of some secondaries. The problem is that when a user is deleted,
    # this foreign key give some errors.
    # FOREIGN KEY (parent_category_id) REFERENCES categories (id_category) ON DELETE RESTRICT

    # TODO: IF A CATEGORY REFER TO ANOTHER ONE (parent_category_id is the same as
    # id_category of the other) THE YEAR AND TYPE SHOULD BE THE SAME
    # EVALUATE IF IT IS NECESSARY TO ADD A CONTROL CHECK BEFORE ADDING THE CATEGORY
    # USING: TRIGGER ... BEFORE INSERT ON ...
    # THE SAME IS TRUE FOR id_user.
    # WE SHOULD ALSO CHECK THAT THE CATEGORY WE ARE REFERENCING TO IS AN expense (IF
    # WE CONSIDER INCOME WITHOUT SECONDRY). THIS CHECK SHOULD ALSO BE DONE DURING EDITING

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id_category INTEGER PRIMARY KEY,
            id_user INTEGER NOT NULL,
            category_year INTEGER,
            name TEXT,
            -- sub category (secondary) have as parent category the primary category
            -- via its id. If the category is a primary this is set to NULL
            parent_category_id INTEGER,
            category_type TEXT NOT NULL CHECK (category_type IN ('expense', 'income')),
        FOREIGN KEY (id_user) REFERENCES users (id_user) ON DELETE CASCADE
        ) STRICT;
        """
    )

    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
            idx_u_idu_year_type_name
        ON
            categories(id_user, category_year, category_type, name)
        WHERE
            parent_category_id IS NULL
        """
    )

    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
            idx_u_idu_year_type_name_idparent
        ON
            categories(id_user, category_year, parent_category_id, name, category_type)
        WHERE
            parent_category_id IS NOT NULL
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS 
            idx_cat_parent 
        ON 
            categories (parent_category_id);
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS 
            idx_cat_lookup
        ON 
            categories(id_user, category_year, category_type, name);
        """
    )

    cursor.close()


def _init_transactions(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()

    # TODO: WHEN DELETING A CATEGORY THE TRANSACTIONS SHOULD BE CONVERTED TO THE
    # NEW CREATED "DELETED" CATEGORY.

    # TODO: THE YEAR (IN tr_date) OF THE TRANSACTION SHOULD MATCH THE YEAR OF THE
    # id_category CONSIDERED. THE SAME IS TRUE FOR THE id_user
    # EVALUATE IF IT IS NECESSARY TO ADD A CONTROL CHECK BEFORE ADDING THE TRANSACTION
    # USING: TRIGGER ... BEFORE INSERT ON ...

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id_tr INTEGER PRIMARY KEY,
            id_user INTEGER NOT NULL,
            id_category INTEGER NOT NULL,
            tr_date TEXT NOT NULL,  -- date formatted as 'YYYY-MM-DD'
            name TEXT,
            tr_value REAL,
            description TEXT,
            currency TEXT,
        FOREIGN KEY (id_user) REFERENCES users (id_user) ON DELETE CASCADE,
        FOREIGN KEY (id_category) REFERENCES categories (id_category)
        ) STRICT;
    """)

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
            idx_tr_id_user_date
        ON
            transactions(id_user, tr_date);
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
            idx_currency
        ON
            transactions(currency);
        """
    )

    cursor.close()


def _init_app_config(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()

    # In this table app configuration parameter can be saved. Example are the app/db
    # version, some usefull dates (e.g. dates used for exchange rates).
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS app_config (
            name TEXT PRIMARY KEY,
            value TEXT 
        );
        """
    )

    cursor.close()


def _init_user_settings(connection: sqlite3.Connection) -> None:
    # Based on: https://stackoverflow.com/questions/10204902/database-design-for-user-settings

    cursor = connection.cursor()

    # User specific settings, like if multi_currency is active or the language are
    # stored in the settings table. Each setting can be either constrained (limited
    # number or values) or uncostrained (virtually infinite number of values).
    # Each setting has a data_type (TEXT) that can be 'real', 'integer', 'bool', 'text'.
    # All the possible values for the costrained settings are stored inside the
    # allowed_settings table. Each allowed setting, that refer to the considered
    # settings with the id_setting column, will store the various values inside the
    # item_value column (TEXT format). The id_allowed_setting is set automatically by
    # the database. The default_value in the settings table, for constrained setting, is
    # the corresponding id_allowed_setting. It mean that it must be defined only after
    # the allowed setting is created. This column is TEXT.
    # User specific settings are stored in the user_settings table. For each setting,
    # identified with the id_setting column will have a value column of type TEXT.
    # For costrained setting the value will be the id_allowed_setting. For uncostrained
    # setting it will be the actual value. Since it is stored as a text, the conversion
    # is done using the data_type column of the corresponding setting.

    # Eample:

    # settings:
    # +------------+------------------+-------------+-----------+---------------+
    # | id_setting |       name       | constrained | data_type | default_value |
    # +------------+------------------+-------------+-----------+---------------+
    # |     10     |      'theme'     |      1      |   'text'  |     '100'     |
    # +------------+------------------+-------------+-----------+---------------+
    # |     11     | 'multi_currency' |      1      |   'bool'  |      '0'      |
    # +------------+------------------+-------------+-----------+---------------+
    # |     12     |    'font_size'   |      0      | 'integer' |      '11'     |
    # +------------+------------------+-------------+-----------+---------------+
    # |     12     |    'language'    |      1      |   'text'  |     '104'     |
    # +------------+------------------+-------------+-----------+---------------+
    # |     14     |    'max_value'   |      0      |   'real'  |    '153.12'   |
    # +------------+------------------+-------------+-----------+---------------+

    # allowed_settings:
    # +--------------------+------------+------------+------------------+
    # | id_allowed_setting | id_setting | item_value |      caption     |
    # +--------------------+------------+------------+------------------+
    # |         100        |     10     |   'dark'   |    'Dark Mode'   |
    # +--------------------+------------+------------+------------------+
    # |         101        |     10     |   'light'  |   'Light Mode'   |
    # +--------------------+------------+------------+------------------+
    # |         102        |     10     |  'system'  | 'System Default' |
    # +--------------------+------------+------------+------------------+
    # |         103        |     13     |    'it'    |     'Italian'    |
    # +--------------------+------------+------------+------------------+
    # |         104        |     13     |    'en'    |     'English'    |
    # +--------------------+------------+------------+------------------+

    # user_settings:
    # +---------+------------+-------+
    # | id_user | id_setting | value |
    # +---------+------------+-------+
    # |   189   |     10     | '101' |
    # +---------+------------+-------+
    # |   189   |     11     |  '1'  |
    # +---------+------------+-------+
    # |   189   |     12     |  '11' |
    # +---------+------------+-------+
    # |   189   |     13     | '104' |
    # +---------+------------+-------+

    # In this case indexes are not needed since unique and primary key already create
    # them

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id_setting INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            constrained INTEGER NOT NULL,
            data_type TEXT NOT NULL CHECK (data_type IN ('text', 'integer', 'bool', 'real')),
            default_value TEXT
        ) STRICT;
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allowed_settings (
            id_allowed_setting INTEGER PRIMARY KEY,
            id_setting INTEGER NOT NULL,
            item_value TEXT NOT NULL,
            caption TEXT,
        FOREIGN KEY (id_setting) REFERENCES settings (id_setting),
        UNIQUE (id_setting, item_value)
        ) STRICT;
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            id_user INTEGER,
            id_setting INTEGER NOT NULL,
            value TEXT,
            FOREIGN KEY (id_user) REFERENCES users (id_user) ON DELETE CASCADE,
            FOREIGN KEY (id_setting) REFERENCES settings (id_setting),
            PRIMARY KEY (id_user, id_setting)
        ) STRICT;
    """)

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_currencies(
            id_user INTEGER NOT NULL,
            currency_code TEXT,
            currency_symbol TEXT,
            FOREIGN KEY (id_user) REFERENCES users (id_user) ON DELETE CASCADE,
            UNIQUE (id_user, currency_code)
            ) STRICT;
        """
    )

    cursor.close()

    _fill_settings(connection)


def _fill_settings(connection: sqlite3.Connection) -> None:
    """Fill settings and allowed settings table with the default values."""
    cursor = connection.cursor()

    sql_settings = """
        INSERT INTO settings (
            name,
            constrained,
            data_type,
            default_value
        )
        VALUES
            (?, ?, ?, ?)
        ON CONFLICT
            (name)
        DO NOTHING
    """

    sql_allowed = """
        INSERT INTO allowed_settings (
            id_setting,
            item_value,
            caption
        )
        VALUES
            (?, ?, ?)
        ON CONFLICT
            (id_setting, item_value)
        DO NOTHING
    """

    sql_edit = """
        UPDATE 
            settings
        SET 
            default_value = ?
        WHERE
            id_setting = ?
    """

    sql_get_id = """
        SELECT
            id_setting
        FROM 
            settings
        WHERE
            name = ?
    """

    settings = default_settings.SETTINGS_DATA

    for setting in settings:
        if setting["constrained"] == 0:
            parameters = (
                setting["name"],
                str(setting["constrained"]),
                setting["data_type"],
                setting["default"],
            )

            cursor.execute(sql_settings, parameters)

        else:
            parameters = (
                setting["name"],
                str(setting["constrained"]),
                setting["data_type"],
                "0",  # Replaced later
            )

            cursor.execute(sql_settings, parameters)

            # If the row is not inserted it means that a conflict happened (i.e.
            # the was already present in the settings table). In that case the
            # rowcount will be 0. We still try to insert the allowed setting
            # because the list might be changed. For this reason we need the
            # correct value of the id_setting of the corresponding setting.
            if cursor.rowcount == 0:
                cursor.execute(sql_get_id, (setting["name"],))
                id_setting = cursor.fetchone()[0]

            else:
                id_setting = cursor.lastrowid

            for all in setting["allowed_settings"]:
                parameters = (id_setting, all["item_value"], all["caption"])
                cursor.execute(sql_allowed, parameters)

                if all["item_value"] == setting["default"]:
                    # edit only if the rows are really new
                    if cursor.rowcount != 0:
                        id_allowed = cursor.lastrowid
                        parameters = (id_allowed, id_setting)
                        cursor.execute(sql_edit, parameters)

    cursor.close()
    # The rowcount check is needed because with this setup the lastrowid
    # will not return None or 0 if a conflict happened
