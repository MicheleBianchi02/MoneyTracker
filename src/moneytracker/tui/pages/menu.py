from rich.console import Console

from moneytracker.tui.pages.category_tab import CategoryPage
from moneytracker.tui.pages.dashboard_tab import DashboardPage
from moneytracker.tui.pages.expense_tab import ExpensePage
from moneytracker.tui.pages.income_tab import IncomePage
from moneytracker.tui.utils import CATEGORY_TAB, DASHBOARD_TAB, EXPENSE_TAB, INCOME_TAB, Page


class MenuPage(Page):
    def __init__(self, id_user: int, active_tab: str) -> None:
        self.id_user = id_user
        self.active_tab = active_tab
        super().__init__()

    def show(self, console: Console) -> None:
        while self.active_tab is not None:
            if self.active_tab == DASHBOARD_TAB:
                self.active_tab = DashboardPage(self.id_user).show(console)

            elif self.active_tab == EXPENSE_TAB:
                self.active_tab = ExpensePage(self.id_user).show(console)

            elif self.active_tab == INCOME_TAB:
                self.active_tab = IncomePage(self.id_user).show(console)

            elif self.active_tab == CATEGORY_TAB:
                self.active_tab = CategoryPage(self.id_user).show(console)

        return None
