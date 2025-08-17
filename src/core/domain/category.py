from dataclasses import dataclass

from pydantic import BaseModel

# NOTE: THE NAME OF THE CATEGORY CAN'T BE ''. CONSIDER THIS IN THE UI


class CategoryIn(BaseModel):
    id_user: int
    year: int
    category_type: str
    primary: str
    secondary: str | None


class CategoryOut(BaseModel):
    id_primary: int
    id_secondary: int | None
    id_user: int
    year: int
    category_type: str
    primary: str
    secondary: str | None


@dataclass
class Category:
    id_user: int
    year: int
    name: str
    parent_category_id: int | None  # None is for instace used for primary
    category_type: str
    id: int = 1  # this value is defined by the database

    def __post_init__(self):
        """The category can only be 'income' or 'expense'."""
        if self.category_type not in ("income", "expense"):
            raise ValueError("category_type must be 'income' or 'expense'")

        if self.name == "":
            raise ValueError("category name can't be ''.")

    def __eq__(self, other):
        """Exclude the id key when equating two category"""

        if not isinstance(other, Category):
            raise NotImplementedError(
                f"Equivalence between Category and {type(other)} is not supported",
            )

        return (
            self.id_user,
            self.year,
            self.name,
            self.parent_category_id,
            self.category_type,
        ) == (
            other.id_user,
            other.year,
            other.name,
            other.parent_category_id,
            other.category_type,
        )
