from pydantic import BaseModel


class Setting(BaseModel):
    id_setting: int
    name: str
    constrained: bool
    allowed_settings: list[dict[str, str]]
    value: str | bool | int | float
