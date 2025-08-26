from rich.console import Console

DASHBOARD_TAB = "dashboard"
EXPENSE_TAB = "expense"
INCOME_TAB = "income"
CATEGORY_TAB = "category"
SETTING_TAB = "setting"


class Page:
    def show(self):
        raise NotImplementedError


def clear_screen() -> None:
    print("\x1b[2J\x1b[H")


def draw_navigation_tab(active_tab: str, console: Console) -> None:
    left_tabs = {
        DASHBOARD_TAB: "Dashboard",
        EXPENSE_TAB: "Expense",
        INCOME_TAB: "Income",
    }
    nav_bar = []
    for tab_id, tab_name in left_tabs.items():
        if tab_id == active_tab:
            nav_bar.append(f"[bold reverse cyan] {tab_name} [/bold reverse cyan]")
        else:
            nav_bar.append(f" {tab_name} ")

    nav_bar.append(" " * 23)

    right_tab = {CATEGORY_TAB: "Category", SETTING_TAB: "Setting"}

    for tab_id, tab_name in right_tab.items():
        if tab_id == active_tab:
            nav_bar.append(f"[bold reverse cyan] {tab_name} [/bold reverse cyan]")
        else:
            nav_bar.append(f" {tab_name} ")

    console.print("  ".join(nav_bar))

    console.print("-" * 80)
