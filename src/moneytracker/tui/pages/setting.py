from rich.console import Console
from rich.prompt import Confirm, Prompt

from moneytracker.core.services.app_config import TUI_MODE_KEY, app_config
from moneytracker.core.services.category_service import CategoryService
from moneytracker.tui.utils import (
    CATEGORY_TAB,
    DASHBOARD_TAB,
    EXPENSE_TAB,
    INCOME_TAB,
    SETTING_TAB,
    Page,
    clear_screen,
    draw_navigation_tab,
)

active_tab = SETTING_TAB

cat_service = CategoryService()

DELETE_SCREEN_MODE = "delete_screen_mode"
ALTERNATE_SCREEN_MODE = "alternate_screen_mode"

TUI_MODE_ID = "TUI_MODE"


class SettingTab(Page):
    def __init__(self, id_user: int) -> None:
        self.id_user = id_user

    def show(self, console: Console) -> str:
        while True:
            clear_screen()

            draw_navigation_tab(active_tab, console)

            self._print_settings(False, console)

            console.print(
                "\nAction: [bold green]e[/]dit, [bold green]c[/]hange tab,  [bold green]q[/]uit"
            )

            choice = Prompt.ask("Choice", choices=["e", "c", "q"], default="c")

            if choice == "q":
                return None

            elif choice == "e":
                self._edit(console)

            elif choice == "c":
                console.print(
                    "\nTabs: [bold green]d[/]ashboard, [bold green]e[/]xpense, "
                    "[bold green]i[/]ncome,  [bold green]c[/]ategory"
                )
                choice = Prompt.ask("Which Tab", choices=["d", "e", "i", "c"], default="d")

                if choice == "d":
                    return DASHBOARD_TAB

                if choice == "e":
                    return EXPENSE_TAB

                elif choice == "i":
                    return INCOME_TAB

                elif choice == "c":
                    return CATEGORY_TAB

    def _print_settings(self, edit: bool, console: Console) -> dict:
        settings = app_config.get_config_settings()

        console.print("\n")

        if edit:
            console.print(f"Identifier: [bold magenta]{TUI_MODE_ID}[/]")
        if settings[TUI_MODE_KEY] == ALTERNATE_SCREEN_MODE:
            console.print("Terminal mode: [bold blue]ALTERNATE_SCREEN[/]")
        elif settings[TUI_MODE_KEY] == DELETE_SCREEN_MODE:
            console.print("Terminal mode: [bold blue]DELETE_SCREEN[/]")
        else:
            console.print("Terminal mode: [bold blue]NONE[/]")

        console.print("\tThis settings is used in terminal mode (no GUI).")
        console.print("\tPossible values are:")
        console.print(
            "\t-[bold green]ALTERNATE_SCREEN[/]: \n\t\tThe app is opened in an alternate terminal screen. "
            "Here vertical scrolling is not allowed."
        )
        console.print(
            "\t\tThis can be problematic for big tables. The terminal history is preserved."
        )

        console.print(
            "\t-[bold green]DELETE_MODE[/]: \n\t\tThe app is opened in the terminal session that run the application."
        )
        console.print(
            "\t\tHere the complete history of terminal session is deleted. "
            "Vertical scrolling is allowed."
        )

        console.print("\t-[bold green]NONE[/]: \n\t\tAsk every time which option to use.")

        return settings

    def _edit(self, console: Console) -> None:
        clear_screen()
        draw_navigation_tab(active_tab, console)

        settings = self._print_settings(True, console)

        console.print("\n[yellow]Edit Setting[/]")

        id = Prompt.ask("Identifier")

        if id == TUI_MODE_ID:
            console.print(
                "Select new TUI mode between: [bold green]ALTERNATE_SCREEN[/], "
                "[bold green]DELETE_SCREEN[/], [bold green]NONE[/]"
            )

            mode_sel = Prompt.ask("Choice", choices=["ALTERNATE_SCREEN", "DELETE_SCREEN", "NONE"])

            if mode_sel == "ALTERNATE_SCREEN":
                mode = ALTERNATE_SCREEN_MODE
            elif mode_sel == "DELETE_SCREEN":
                mode = DELETE_SCREEN_MODE
            elif mode_sel == "NONE":
                mode = None

            if settings[TUI_MODE_KEY] == ALTERNATE_SCREEN_MODE:
                mode_pre = "ALTERNATE_SCREEN"
            elif settings[TUI_MODE_KEY] == DELETE_SCREEN_MODE:
                mode_pre = "DELETE_SCREEN"
            else:
                mode_pre = "NONE"

            console.print()
            console.print("[bold magenta]TUI_MODE:[/]")
            console.print(f"{mode_pre} -> {mode_sel}")

            is_ok = Confirm.ask("\nDo you want to edit it?")

            if is_ok:
                try:
                    app_config.edit_config(key=TUI_MODE_KEY, value=mode)
                except Exception:
                    console.print("\n[red]An error occoured, please try again[/]")
                    Prompt.ask("")
                    return
                console.print("[green]Setting successfully modified[/]")
            else:
                console.print("[red]Operation canceled[/]")

            Prompt.ask("")
            return

        else:
            console.print("[red]This identifier doesn't exist. Please try again[/]")
            Prompt.ask("")
