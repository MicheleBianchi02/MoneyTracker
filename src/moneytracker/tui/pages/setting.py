from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from moneytracker.core.domain.exchange_rate import Currency
from moneytracker.core.services.app_config import TUI_MODE_KEY, app_config
from moneytracker.core.services.category_service import CategoryService
from moneytracker.core.services.user_setting_service import UserSettingService
from moneytracker.infrastructure.dependencies import manage_uow
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
CURRENCIES_ID = "CURRENCIES"

USER_CURR_KEY = "user_currencies"
AVAILABLE_CURR_KEY = "available_currencies"


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

        # ---- CURRENCIES ----

        if edit:
            console.print(f"Identifier: [bold magenta]{CURRENCIES_ID}[/]")

        with manage_uow() as uow:
            user_currencies = UserSettingService().get_currency_list(uow, self.id_user, None)

        curr_table = Table(title="[bold blue]CURRENCIES[/]")
        curr_table.add_column("Code")
        curr_table.add_column("Symbol")
        curr_table.add_column("Name")

        code_list = []
        for curr in user_currencies:
            curr_table.add_row(curr.code, curr.symbol, curr.name)
            code_list.append(curr.code)

        settings[USER_CURR_KEY] = user_currencies

        console.print(curr_table)

        if edit:
            available_table = Table(title="AVAILABLE CURRENCIES")
            available_table.add_column("Code")
            available_table.add_column("Symbol")
            available_table.add_column("Name")

            with manage_uow() as uow:
                available_currencies = UserSettingService().get_currency_list(uow, None, None)

            for curr in available_currencies:
                if curr.code not in code_list:
                    available_table.add_row(f"[bold green]{curr.code}[/]", curr.symbol, curr.name)
                    code_list.append(curr.code)

            settings[AVAILABLE_CURR_KEY] = available_currencies
            console.print(available_table)

        console.print("\n\n")

        # ----- TUI MODE ----
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
            "\t-[bold green]DELETE_SCREEN[/]: \n\t\tThe app is opened in the terminal session that run the application."
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

        elif id == CURRENCIES_ID:
            choice = Prompt.ask(
                "You want to add a new currency or remove an existing one", choices=["a", "r"]
            )
            if choice == "a":
                available_curr: list[Currency] = settings[AVAILABLE_CURR_KEY]
                while True:
                    new_code = Prompt.ask("Select the code inside the available currencies' table")

                    new_code = new_code.upper()

                    for curr in available_curr:
                        if curr.code == new_code:
                            if not curr.is_active:
                                console.print(
                                    f"\nThis currency is no more available since {curr.deprecation_date.isoformat()}"
                                )
                                console.print("You can use it only for dates past the date above.")

                            else:
                                console.print()

                            break
                    else:
                        console.print("[red]Please select a valid currency's code[/]")
                        continue

                    break

                console.print("[bold magenta]CURRENCY:[/]")
                console.print(f"Code: {curr.code}")
                console.print(f"Symbol: {curr.symbol}")
                console.print(f"Name: {curr.name}")

                is_ok = Confirm.ask("\nDo you want to add it?")

                if is_ok:
                    try:
                        with manage_uow() as uow:
                            UserSettingService().add_currency(uow, self.id_user, new_code)
                    except Exception:
                        console.print("\n[red]An error occoured, please try again[/]")
                        Prompt.ask("")
                        return
                    console.print("[green]Setting successfully modified[/]")
                else:
                    console.print("[red]Operation canceled[/]")

                Prompt.ask("")
                return

            elif choice == "r":
                user_curr: list[Currency] = settings[USER_CURR_KEY]

                if len(user_curr) == 1:
                    console.print("[red]You can't have 0 currencies[/]")
                    Prompt.ask("")
                    return

                while True:
                    rm_code = Prompt.ask("Select the code inside the currencies' table")
                    rm_code = rm_code.upper()

                    for curr in user_curr:
                        if curr.code == rm_code:
                            break

                    else:
                        console.print("[red]Please select a valid currency's code[/]")
                        continue

                    break

                console.print()
                console.print("[bold magenta]CURRENCY:[/]")
                console.print(f"Code: {curr.code}")
                console.print(f"Symbol: {curr.symbol}")
                console.print(f"Name: {curr.name}")

                is_ok = Confirm.ask("\nDo you want to remove it?")

                if is_ok:
                    try:
                        with manage_uow() as uow:
                            UserSettingService().delete_currency(uow, self.id_user, rm_code)
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
