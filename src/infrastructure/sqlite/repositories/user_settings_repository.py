import json
import sqlite3

from src.core.domain.setting import Setting
from src.core.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    ForeignKeyError,
    RepositoryError,
)
from src.core.repositories.abstract_user_setting_repository import AbstractUserSettingRepository


class UserSettingRepository(AbstractUserSettingRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(
        self,
        id_user: int,
        setting_name: str,
        value: int | float | str | bool,
    ) -> None:
        cursor = self._connection.cursor()

        # If the setting is already present in the db it is updated
        sql = """
            INSERT INTO user_settings(
                id_user, 
                id_setting,
                value)
            VALUES
                (?, ?, ?)
            ON CONFLICT
                (id_user, id_setting)
            DO UPDATE SET
                value=excluded.value;
        """

        try:
            # value is converted because _get_allowed_id require a str value
            if isinstance(value, bool):
                if value:
                    value = "1"
                else:
                    value = "0"

            else:
                value = str(value)

            id_setting, is_constrained = self._get_id_setting_constrained(setting_name)

            if is_constrained:
                id_allowed = self._get_allowed_id(id_setting, value)
                value_i = str(id_allowed)  # in the db it is saved as str

            else:
                value_i = value

            parameters = (id_user, id_setting, value_i)

            cursor.execute(sql, parameters)
            cursor.close()

        except sqlite3.DatabaseError as e:
            if "FOREIGN KEY constraint failed" in str(e):
                raise ForeignKeyError("Foreign key error") from e

            raise RepositoryError(
                "Error while adding user specific setting: "
                f"id_user:{id_user}, "
                f"setting_name:{setting_name}, "
                f"value:{value}. "
            ) from e

    def _get_id_setting_constrained(self, setting_name: str) -> tuple[int, bool]:
        """Return the id_setting and constrained of the setting with the given name.

        setting_name is a string."""

        cursor = self._connection.cursor()

        sql = """
            SELECT
                id_setting,
                constrained
            FROM
                settings
            WHERE 
                name = ?
        """
        parameters = (setting_name,)
        cursor.execute(sql, parameters)

        sett_get = cursor.fetchone()
        cursor.close()

        if sett_get is None:
            raise EntityNotFoundError("setting", f"setting_name:{setting_name}")

        id_str = sett_get[0]
        constrained = True if sett_get[1] == 1 else False

        return int(id_str), constrained

    def _get_allowed_id(self, id_setting: int, value: str) -> int:
        """Get the id_allowed_setting corresponding to the given item_value.

        value should be a string."""

        cursor = self._connection.cursor()

        sql = """
            SELECT 
                id_allowed_setting
            FROM 
                allowed_settings
            WHERE
                id_setting = ? AND item_value = ?
        """
        parameters = (id_setting, value)

        cursor.execute(sql, parameters)

        id_str = cursor.fetchone()
        cursor.close()
        if id_str is None:
            raise EntityNotFoundError(
                "allowed_setting",
                f"id_setting:{id_setting}, item_value:{value}",
            )

        id_str = id_str[0]

        return int(id_str)

    def get(self, id_user: int | None, setting_name: str | None = None) -> list[Setting]:
        cursor = self._connection.cursor()

        # When id_user is None, the condition us.id_user = NULL in the query always
        # evalueates to false (even if us.id_usert is NULL, for that IS NULL should be
        # used). It means that all the column of the joined table referring to us
        # will evaluate to NULL. This is requested, since in this case the default
        # value is returned.
        # With coalesce we select the first non NULL element.
        # sqlite3 doesn't convert json_group_array automatically (the allowed_settings_json
        # column). The output will be a string that need to be converted to a list of
        # dictionaries. Even if the allowed value is only one, the group_array will
        # still put it inside a list.
        sql = """
        SELECT
            s.id_setting,
            s.name,
            s.constrained,
            s.data_type,
            -- This CASE block calculates the final value for the setting.
            -- It checks if the setting is constrained and uses the correct value.
            CASE
                WHEN s.constrained = 0 THEN
                    -- If not constrained, use the user's value, or fall back to the default.
                    COALESCE(us.value, s.default_value)
                ELSE
                    -- If constrained, find the item_value from allowed_settings that
                    -- corresponds to the user's ID or the default ID.
                    (SELECT a_s.item_value
                     FROM allowed_settings AS a_s
                     WHERE 
                        a_s.id_allowed_setting = CAST(COALESCE(us.value, s.default_value) AS INTEGER))
            END AS final_value,
            -- This subquery gathers all allowed settings into a single JSON field.
            (SELECT json_group_array(json_object('item_value', item_value, 'caption', caption))
             FROM allowed_settings
             WHERE id_setting = s.id_setting) AS allowed_settings_json
        FROM
            settings AS s
        LEFT JOIN
            -- when ? is NULL the join will always evaluate to FALSE
            user_settings AS us ON s.id_setting = us.id_setting AND us.id_user = ? 
        """
        if setting_name is not None:
            sql += "WHERE s.name = ?"
            parameters = (id_user, setting_name)
        else:
            parameters = (id_user,)

        try:
            cursor.execute(sql, parameters)
            settings = cursor.fetchall()

            setting_list = []

            for sett in settings:
                id_setting = sett[0]
                name = sett[1]
                data_type = sett[3]
                is_constrained = True if sett[2] == 1 else False
                allo_settings = sett[5]
                allo_settings = json.loads(allo_settings)
                value = sett[4]
                value = _convert_value(data_type, value)

                if is_constrained:
                    for allo in allo_settings:
                        all_value = allo["item_value"]
                        allo["item_value"] = _convert_value(data_type, all_value)

                setting = Setting(
                    id_setting=id_setting,
                    name=name,
                    constrained=is_constrained,
                    allowed_settings=allo_settings,
                    value=value,
                )

                setting_list.append(setting)

            cursor.close()
            return setting_list

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                f"Error while gettin setting list for: "
                f"id_user:{id_user}, "
                f"setting_name:{setting_name}, "
            ) from e

    def add_currency(
        self,
        id_user: int,
        currency_code: str,
        currency_symbol: str | None,
    ) -> None:
        cursor = self._connection.cursor()

        sql = """
            INSERT INTO user_currencies(
                id_user,
                currency_code,
                currency_symbol)
            VALUES
                (?, ?, ?)
        """

        parameters = (id_user, currency_code, currency_symbol)

        try:
            cursor.execute(sql, parameters)
            cursor.close()

        except sqlite3.DatabaseError as e:
            if "FOREIGN KEY constraint failed" in str(e):
                raise ForeignKeyError("Foreign key error") from e
            elif "UNIQUE constraint failed" in str(e):
                raise DuplicateEntityError("Unique constrainnt error") from e

            raise RepositoryError(
                "Error while adding user specific currency: "
                f"id_user:{id_user}, "
                f"currency_code:{currency_code}, "
                f"currency_symbol:{currency_symbol}. "
            ) from e

    def get_currency_list(self, id_user: int) -> list[tuple[str, str]]:
        cursor = self._connection.cursor()

        sql = """
            SELECT
                currency_code,
                currency_symbol
            FROM 
                user_currencies
            WHERE
                id_user = ?
        """
        parameters = (id_user,)

        try:
            cursor.execute(sql, parameters)
            res = cursor.fetchall()
            cursor.close()

            return res

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                f"Error while getting currencies for user with: id_user:{id_user}",
            ) from e

    def delete_currency(self, id_user: int, currency_code: str) -> None:
        cursor = self._connection.cursor()

        sql = """
            DELETE FROM
                user_currencies
            WHERE
                id_user = ? AND currency_code = ?
        """

        parameters = (id_user, currency_code)

        self._validate_delete_currency(id_user, currency_code)

        try:
            cursor.execute(sql, parameters)
            cursor.close()

        except sqlite3.DatabaseError as e:
            raise RepositoryError(
                f"Error while deleting user specific currency: currency_code:{currency_code}. "
            ) from e

    def _validate_delete_currency(self, id_user: int, currency_code: str) -> None:
        """Check if the currency with the given parameters exist in the db.

        If nothing is found an EntityNotFoundError is raised.
        """

        cursor = self._connection.cursor()

        sql = """
            SELECT 1
            FROM
                user_currencies
            WHERE
                id_user = ? AND currency_code = ?
        """

        parameters = (id_user, currency_code)

        curr_get = cursor.execute(sql, parameters).fetchone()
        cursor.close()

        if curr_get is None:
            raise EntityNotFoundError(
                "user_currency",
                f"id_user:{id_user}, currency_code:{currency_code} ",
            )


def _convert_value(data_type: str, value: str) -> str | int | float | bool:
    """Convert the output of the database into the real value depending on the
    data_type"""

    if data_type == "bool":
        if value == "1":
            return True
        else:
            return False
    elif data_type == "integer":
        return int(value)
    elif data_type == "text":
        return str(value)
    elif data_type == "real":
        return float(value)
