from src.core.domain.setting import Setting
from src.core.exceptions import EntityNotFoundError, DuplicateEntityError
from src.core.repositories.abstract_user_setting_repository import AbstractUserSettingRepository

# Simplified default settings for the fake repository
FAKE_SETTINGS_DATA = {
    "theme": {
        "id": 1, "constrained": True, "data_type": "text", "default": "dark",
        "allowed": [{"item_value": "dark", "caption": "Dark Mode"}, {"item_value": "light", "caption": "Light Mode"}]
    },
    "font_size": {
        "id": 2, "constrained": False, "data_type": "integer", "default": 12, "allowed": []
    }
}

class FakeUserSettingRepository(AbstractUserSettingRepository):
    def __init__(self):
        self._user_settings = {} # {id_user: {setting_name: value}}
        self._user_currencies = {} # {id_user: [(code, symbol)]}

    def add(
        self,
        id_user: int,
        setting_name: str,
        value: int | float | str | bool,
    ) -> None:
        if setting_name not in FAKE_SETTINGS_DATA:
            raise EntityNotFoundError("setting", f"setting_name:{setting_name}")
        
        if id_user not in self._user_settings:
            self._user_settings[id_user] = {}
        
        self._user_settings[id_user][setting_name] = value

    def get(self, id_user: int | None, setting_name: str | None = None) -> list[Setting]:
        settings_to_return = []
        
        target_settings = FAKE_SETTINGS_DATA.keys()
        if setting_name:
            if setting_name not in FAKE_SETTINGS_DATA:
                return []
            target_settings = [setting_name]

        for name in target_settings:
            setting_def = FAKE_SETTINGS_DATA[name]
            user_val = None
            if id_user and id_user in self._user_settings:
                user_val = self._user_settings[id_user].get(name)
            
            final_value = user_val if user_val is not None else setting_def["default"]

            settings_to_return.append(Setting(
                id_setting=setting_def["id"],
                name=name,
                constrained=setting_def["constrained"],
                allowed_settings=setting_def["allowed"],
                value=final_value
            ))
        return settings_to_return

    def add_currency(
        self,
        id_user: int,
        currency_code: str,
        currency_symbol: str | None,
    ) -> None:
        if id_user not in self._user_currencies:
            self._user_currencies[id_user] = []
        
        if any(c[0] == currency_code for c in self._user_currencies[id_user]):
            raise DuplicateEntityError("Currency code already exists for this user.")

        self._user_currencies[id_user].append((currency_code, currency_symbol))

    def get_currency_list(self, id_user: int) -> list[tuple[str, str]]:
        return self._user_currencies.get(id_user, [])

    def delete_currency(self, id_user: int, currency_code: str) -> None:
        if id_user not in self._user_currencies:
            raise EntityNotFoundError("user_currency", f"id_user:{id_user}")
        
        currency_list = self._user_currencies[id_user]
        curr_to_del = next((c for c in currency_list if c[0] == currency_code), None)

        if not curr_to_del:
            raise EntityNotFoundError("user_currency", f"currency_code:{currency_code}")
        
        currency_list.remove(curr_to_del)
