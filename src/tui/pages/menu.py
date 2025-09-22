from rich.console import Console

from tui.pages.dashboard_tab import DashboardPage
from tui.pages.expense_tab import ExpensePage
from tui.utils import DASHBOARD_TAB, EXPENSE_TAB, Page


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

        return None
