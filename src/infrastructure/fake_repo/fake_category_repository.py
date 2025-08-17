from src.core.domain.category import Category, CategoryIn, CategoryOut
from src.core.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    InvalidParameterError,
)
from src.core.repositories.abstract_category_repository import AbstractCategoryRepository


class FakeCategoryRepository(AbstractCategoryRepository):
    def __init__(self, categories: list[Category] | None = None):
        self._categories = categories if categories is not None else []
        self._next_id = len(self._categories) + 1

    def add(self, cat_list: list[CategoryIn] | CategoryIn) -> None:
        if not isinstance(cat_list, list):
            cat_list = [cat_list]

        for cat_in in cat_list:
            if cat_in.category_type not in ("income", "expense"):
                raise InvalidParameterError("category_type must be 'income' or 'expense'")
            if cat_in.category_type == "income" and cat_in.secondary is not None:
                raise InvalidParameterError("income can't have secondaries.")

            # Check for primary category
            primary_cat = self._get_category_by_details(
                cat_in.id_user, cat_in.year, cat_in.category_type, cat_in.primary, None
            )

            if primary_cat is None:
                primary_cat = Category(
                    id=self._next_id,
                    id_user=cat_in.id_user,
                    year=cat_in.year,
                    name=cat_in.primary,
                    parent_category_id=None,
                    category_type=cat_in.category_type,
                )
                self._categories.append(primary_cat)
                self._next_id += 1
            
            if cat_in.secondary:
                secondary_cat = self._get_category_by_details(
                    cat_in.id_user, cat_in.year, cat_in.category_type, cat_in.primary, cat_in.secondary
                )
                if secondary_cat is not None:
                    raise DuplicateEntityError("Secondary category already exists.")

                new_secondary = Category(
                    id=self._next_id,
                    id_user=cat_in.id_user,
                    year=cat_in.year,
                    name=cat_in.secondary,
                    parent_category_id=primary_cat.id,
                    category_type=cat_in.category_type,
                )
                self._categories.append(new_secondary)
                self._next_id += 1

    def get_primary_list(
        self, id_user: int, year: int | None, cat_type: str | None
    ) -> list[CategoryOut]:
        primaries = [
            c for c in self._categories 
            if c.id_user == id_user 
            and c.parent_category_id is None
        ]
        if year:
            primaries = [c for c in primaries if c.year == year]
        if cat_type:
            primaries = [c for c in primaries if c.category_type == cat_type]
        
        return [
            CategoryOut(
                id_primary=c.id,
                id_secondary=None,
                id_user=c.id_user,
                year=c.year,
                category_type=c.category_type,
                primary=c.name,
                secondary=None,
            ) for c in primaries
        ]

    def get_secondary_list(
        self, id_user: int, year: int | None, primary: str | None
    ) -> list[CategoryOut]:
        secondaries = [
            c for c in self._categories 
            if c.id_user == id_user 
            and c.parent_category_id is not None
        ]
        if year:
            secondaries = [c for c in secondaries if c.year == year]

        output = []
        for sec in secondaries:
            prim = self._get_category_by_id(sec.parent_category_id)
            if prim:
                if primary is None or prim.name == primary:
                    output.append(
                        CategoryOut(
                            id_primary=prim.id,
                            id_secondary=sec.id,
                            id_user=sec.id_user,
                            year=sec.year,
                            category_type=sec.category_type,
                            primary=prim.name,
                            secondary=sec.name,
                        )
                    )
        return output

    def get(
        self, id_user: int, year: int | None, cat_type: str | None
    ) -> list[CategoryOut]:
        cats = [c for c in self._categories if c.id_user == id_user]
        if year:
            cats = [c for c in cats if c.year == year]
        if cat_type:
            cats = [c for c in cats if c.category_type == cat_type]

        output = []
        for c in cats:
            if c.parent_category_id is None: # is primary
                output.append(CategoryOut(
                    id_primary=c.id,
                    id_secondary=None,
                    id_user=c.id_user,
                    year=c.year,
                    category_type=c.category_type,
                    primary=c.name,
                    secondary=None,
                ))
            else: # is secondary
                prim = self._get_category_by_id(c.parent_category_id)
                if prim:
                    output.append(CategoryOut(
                        id_primary=prim.id,
                        id_secondary=c.id,
                        id_user=c.id_user,
                        year=c.year,
                        category_type=c.category_type,
                        primary=prim.name,
                        secondary=c.name,
                    ))
        return output

    def get_id(
        self, id_user: int, year: int, cat_type: str, primary: str, secondary: str | None
    ) -> int | None:
        cat = self._get_category_by_details(id_user, year, cat_type, primary, secondary)
        return cat.id if cat else None

    def edit(self, id_cat: int, new_name: str) -> None:
        cat = self._get_category_by_id(id_cat)
        if not cat:
            raise EntityNotFoundError("category", f"id_cat:{id_cat}")
        cat.name = new_name

    def delete(self, id_cat: int) -> None:
        cat = self._get_category_by_id(id_cat)
        if not cat:
            raise EntityNotFoundError("category", f"id_cat:{id_cat}")
        
        if cat.parent_category_id is None:
            if any(c.parent_category_id == id_cat for c in self._categories):
                pass

        self._categories.remove(cat)

    def _get_category_by_id(self, id_cat: int) -> Category | None:
        return next((c for c in self._categories if c.id == id_cat), None)

    def _get_category_by_details(
        self, id_user: int, year: int, cat_type: str, primary: str, secondary: str | None
    ) -> Category | None:
        if secondary is None: # looking for primary
            return next((
                c for c in self._categories
                if c.id_user == id_user
                and c.year == year
                and c.category_type == cat_type
                and c.name == primary
                and c.parent_category_id is None
            ), None)
        else: # looking for secondary
            primary_cat = self._get_category_by_details(id_user, year, cat_type, primary, None)
            if not primary_cat:
                return None
            return next((
                c for c in self._categories
                if c.id_user == id_user
                and c.year == year
                and c.category_type == cat_type
                and c.name == secondary
                and c.parent_category_id == primary_cat.id
            ), None)
