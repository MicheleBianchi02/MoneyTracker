from datetime import date

from src.core.domain.category import CategoryOut
from src.core.domain.transaction import Transaction, TransactionIn, TransactionOut
from src.core.exceptions import EntityNotFoundError
from src.core.repositories.abstract_transaction_repository import AbstractTransactionRepository
from src.infrastructure.fake_repo.fake_category_repository import FakeCategoryRepository


class FakeTransactionRepository(AbstractTransactionRepository):
    def __init__(
        self, category_repo: FakeCategoryRepository, transactions: list[Transaction] | None = None
    ):
        self._transactions = transactions if transactions is not None else []
        self._category_repo = category_repo
        self._next_id = len(self._transactions) + 1

    def add(self, transaction_list: list[TransactionIn] | TransactionIn) -> None:
        if not isinstance(transaction_list, list):
            transaction_list = [transaction_list]

        for tr_in in transaction_list:
            id_category = self._category_repo.get_id(
                tr_in.id_user,
                tr_in.tr_date.year,
                tr_in.tr_type,
                tr_in.primary,
                tr_in.secondary,
            )
            if id_category is None:
                raise EntityNotFoundError("Category not found")

            new_tr = Transaction(
                id=self._next_id,
                id_user=tr_in.id_user,
                id_category=id_category,
                date=tr_in.tr_date,
                name=tr_in.name,
                value=tr_in.value,
                currency=tr_in.currency,
                description=tr_in.description,
            )
            self._transactions.append(new_tr)
            self._next_id += 1

    def get(
        self,
        id_user: int,
        begin_date: date | None,
        end_date: date | None,
        tr_type: str | None = None,
        primary: str | None = None,
        secondary: str | None = None,
    ) -> list[TransactionOut]:
        if begin_date is None:
            begin_date = date.min
        if end_date is None:
            end_date = date.max

        user_transactions = [
            t
            for t in self._transactions
            if t.id_user == id_user and begin_date <= t.date <= end_date
        ]

        output = []
        for tr in user_transactions:
            cat = self._category_repo._get_category_by_id(tr.id_category)
            if not cat:
                continue

            cat_out = None
            if cat.parent_category_id is None:  # primary
                cat_out = CategoryOut(
                    id_primary=cat.id,
                    id_secondary=None,
                    id_user=cat.id_user,
                    year=cat.year,
                    category_type=cat.category_type,
                    primary=cat.name,
                    secondary=None,
                )
            else:
                prim = self._category_repo._get_category_by_id(cat.parent_category_id)
                if prim:
                    cat_out = CategoryOut(
                        id_primary=prim.id,
                        id_secondary=cat.id,
                        id_user=cat.id_user,
                        year=cat.year,
                        category_type=cat.category_type,
                        primary=prim.name,
                        secondary=cat.name,
                    )

            if not cat_out:
                continue

            # Filtering
            if tr_type and cat_out.category_type != tr_type:
                continue
            if primary and cat_out.primary != primary:
                continue
            if secondary and cat_out.secondary != secondary:
                continue

            output.append(
                TransactionOut(
                    id=tr.id,
                    id_user=tr.id_user,
                    primary=cat_out.primary,
                    secondary=cat_out.secondary,
                    tr_type=cat_out.category_type,
                    tr_date=tr.date,
                    name=tr.name,
                    value=tr.value,
                    currency=tr.currency,
                    description=tr.description,
                )
            )
        return output

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
        # This is a simplified implementation for testing purposes.
        # It does not perform currency conversion.
        transactions = self.get(id_user, begin_date, end_date, tr_type, primary, secondary)

        summary = {}
        all_rates_updated = True  # Fake value

        # TODO: Add currency conversion

        for tr in transactions:
            if tr.currency != to_currency:
                # This fake repository does not support currency conversion.
                # For testing, ensure transactions have the same currency as `to_currency`.
                pass

            prim_key = tr.primary
            sec_key = tr.secondary if tr.secondary else "N/A"
            month_key = tr.tr_date.strftime("%Y-%m")

            if prim_key not in summary:
                summary[prim_key] = {}
            if sec_key not in summary[prim_key]:
                summary[prim_key][sec_key] = {}

            summary[prim_key][sec_key][month_key] = (
                summary[prim_key][sec_key].get(month_key, 0.0) + tr.value
            )

        return summary, all_rates_updated

    def edit(self, id_tr: int, new_tr: TransactionIn) -> None:
        tr = next((t for t in self._transactions if t.id == id_tr), None)
        if not tr:
            raise EntityNotFoundError("transaction", f"id_tr:{id_tr}")

        id_category = self._category_repo.get_id(
            new_tr.id_user,
            new_tr.tr_date.year,
            new_tr.tr_type,
            new_tr.primary,
            new_tr.secondary,
        )
        if id_category is None:
            raise EntityNotFoundError("Category not found")

        tr.id_category = id_category
        tr.date = new_tr.tr_date
        tr.name = new_tr.name
        tr.value = new_tr.value
        tr.description = new_tr.description
        tr.currency = new_tr.currency

    def delete(self, id_tr: int) -> None:
        tr = next((t for t in self._transactions if t.id == id_tr), None)
        if not tr:
            raise EntityNotFoundError("transaction", f"id_tr:{id_tr}")
        self._transactions.remove(tr)
