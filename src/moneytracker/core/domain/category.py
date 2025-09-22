from typing import Literal

from pydantic import BaseModel

# NOTE: THE NAME OF THE CATEGORY CAN'T BE ''. CONSIDER THIS IN THE UI


class CategoryIn(BaseModel):
    year: int
    category_type: Literal["income", "expense"]
    primary: str
    secondary: str | None


class CategoryOut(BaseModel):
    id_primary: int
    id_secondary: int | None
    id_user: int
    year: int
    category_type: Literal["income", "expense"]
    primary: str
    secondary: str | None
