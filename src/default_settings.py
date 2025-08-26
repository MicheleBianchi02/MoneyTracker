# This file contain all the user-settings default value.
# It will be used the first time the database is created.

"""
RULES:
    - the parameter of this list should not be modified after the database is created.
        Otherwise another setting will be created, without removing the other.
    - It is only possible to add setting (dict) to this list after the database is
        created. Removing them will not change anything.
    - "name" must be unique
    - for uncostrained setting (constrained == 1) the "default" key must be a str. If
        the data_type is boll, the value must be "1" or "0" (not "True" or "False")
    - if the setting is constrained, the allowed_settings key must be a list containing
        dictionaries.
    - the default value for constrained settings is the item_name of the corresponding
        allowed settings. Even if numeric, the value must be a str.
    - the item_name of an allowed setting must be unique for that setting. Two allowed
        setting can have the same item_value if they pertain to different setting.
    - the value for the constrained key must be of type int. 1 if the setting is
        constrained, 0 otherwise.
    - all the item_value in the allowed_settings list must be in str form, even if
        data_type is not text
"""

DEFAULT_CURRENCY_NAME = "default_currency"


SETTINGS_DATA = [
    {
        "name": "value_format",
        "constrained": 1,
        "data_type": "text",
        "allowed_settings": [
            {"item_value": "comma_dot", "caption": "1,000.00"},
            {"item_value": "dot_comma", "caption": "1.000,00"},
            {"item_value": "space_comma", "caption": "1 000,00"},
            {"item_value": "space_dot", "caption": "1 000.00"},
            {"item_value": "apo_dot", "caption": "1'000.00"},
            {"item_value": "apo_comma", "caption": "1'000,00"},
            {"item_value": "indian", "caption": "1,00,000.00"},
            {"item_value": "scientific", "caption": "1.00e+3"},
            {"item_value": "no_separator", "caption": "1000.00"},
        ],
        "default": "comma_dot",
    },
    {
        "name": "theme",
        "constrained": 1,
        "data_type": "text",
        "allowed_settings": [
            {"item_value": "system", "caption": "System Default"},
            {"item_value": "dark", "caption": "Dark Mode"},
            {"item_value": "light", "caption": "Light Mode"},
        ],
        "default": "system",
    },
    {
        "name": "multi_currency_active",
        "constrained": 0,
        "data_type": "bool",
        "allowed_settings": [],
        "default": "1",  # same as true
    },
    {
        "name": "font_size",
        "constrained": 0,
        "data_type": "integer",
        "allowed_settings": [],
        "default": "11",
    },
    {
        "name": "language",
        "constrained": 1,
        "data_type": "text",
        "allowed_settings": [
            {"item_value": "en", "caption": "English"},
            {"item_value": "it", "caption": "Italiano"},
            {"item_value": "fr", "caption": "Français"},
        ],
        "default": "en",
    },
    {
        "name": DEFAULT_CURRENCY_NAME,
        "constrained": 0,
        "data_type": "text",
        "allowed_settings": [],
        "default": "EUR",
    },
]
