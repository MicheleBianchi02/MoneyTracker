from datetime import date

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from moneytracker.core.services.category_service import CategoryService
from moneytracker.core.services.transaction_service import TransactionService
from moneytracker.core.services.user_setting_service import UserSettingService
from moneytracker.default_settings import DEFAULT_CURRENCY_NAME
from moneytracker.infrastructure.dependencies import manage_uow
from moneytracker.infrastructure.sqlite.repositories.transaction_repository import NONE_REPLACEMENT
from moneytracker.tui.utils import (
    DASHBOARD_TAB,
    EXPENSE_TAB,
    Page,
    clear_screen,
    draw_navigation_tab,
)
from moneytracker.utils import format_value

active_tab = EXPENSE_TAB


tr_service = TransactionService()
setting_service = UserSettingService()
cat_service = CategoryService()

# None replacement for keys in the returned dictionary
none_key = NONE_REPLACEMENT


class ExpensePage(Page):
    def __init__(self, id_user: int) -> None:
        self.id_user = id_user

        with manage_uow() as uow:
            setting = setting_service.get(uow, id_user, "value_format")[0]
            self.value_format = setting.value

            # code used to dissplay all cat in the filter
            self._cat_code = "ncsk8swedmsf402323"

            self.curr_list = setting_service.get_currency_list(uow, self.id_user)
            self.default_currency = setting_service.get(uow, self.id_user, DEFAULT_CURRENCY_NAME)

        if not self.default_currency:
            self.default_currency = None
        else:
            self.default_currency = self.default_currency[0].value

    def show(self, console: Console) -> str:
        year = date.today().year

        st_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        filters = {
            "st_date": st_date,
            "end_date": end_date,
            "currency": self.default_currency,
            "show_sec": True,
        }

        while True:
            clear_screen()

            draw_navigation_tab(active_tab, console)

            self._draw_table(filters, console)

            console.print(
                "\nAction: [bold green]f[/]ilter, [bold green]c[/]hange tab, [bold green]q[/]uit"
            )

            choice = Prompt.ask("Choice", choices=["f", "c", "q"], default="c")

            if choice == "q":
                return None

            elif choice == "c":
                console.print(
                    "\nTabs: [bold green]d[/]ashboard, [bold green]i[/]ncome, "
                    "[bold green]c[/]ategory, [bold green]s[/]ettings"
                )
                choice = Prompt.ask("Which Tab", choices=["d", "i", "c", "s"], default="d")

                if choice == "d":
                    return DASHBOARD_TAB

            elif choice == "f":
                filters = self._filter(filters, console)

    def _draw_table(
        self,
        filters: dict[str, str | date | bool],
        console: Console,
    ) -> None:
        st_date = filters["st_date"]
        end_date = filters["end_date"]
        show_sec = filters["show_sec"]
        currency = filters["currency"]

        with manage_uow() as uow:
            summary, is_valid = tr_service.get_summary(
                uow,
                self.id_user,
                st_date,
                end_date,
                "expense",
                currency,
                None,
                None,
            )

        table = Table()
        table.add_column("Category")
        table.add_column("Subcategory")
        table.add_column("Jan")
        table.add_column("Feb")
        table.add_column("Mar")
        table.add_column("Apr")
        table.add_column("May")
        table.add_column("Jun")
        table.add_column("Jul")
        table.add_column("Aug")
        table.add_column("Sep")
        table.add_column("Oct")
        table.add_column("Nov")
        table.add_column("Dec")
        table.add_column("Total")

        rows = []
        for prim, res in summary.items():
            prim_row = [0] * 15
            prim_row[0] = prim
            prim_row[1] = ""
            sec_row_list = []
            for sec, val in res.items():
                if sec != none_key:
                    sec_row = [0] * 15
                    # sec_row[0] = prim
                    sec_row[0] = ""
                    sec_row[1] = sec

                    for sum_date, value in val.items():
                        # There can be multiple years, so we have to sum the months
                        month = int(sum_date[5:])
                        prim_row[month + 1] += value
                        sec_row[month + 1] += value

                    sec_row_list.append(sec_row)

                else:
                    for sum_date, value in val.items():
                        # There can be multiple years, so we have to sum the months
                        month = int(sum_date[5:])
                        prim_row[month + 1] += value

            rows.append(prim_row)
            rows.extend(sec_row_list)

        total_row = [0] * 15
        total_row[0] = "Total"
        total_row[1] = ""
        for row in rows:
            row[-1] = sum(row[2:])  # right Total
            for idx, val in enumerate(row[2:]):
                total_row[idx + 2] += val

            row[2:] = [format_value(par, self.value_format) for par in row[2:]]
            if row[1] == "":  # primary row
                table.add_row(*row, style="on blue")
            elif show_sec:  # secondary row
                table.add_row(*row)

        table.add_row("")

        total_row[2:] = [format_value(par, self.value_format) for par in total_row[2:]]
        table.add_row(*total_row, style="on green")

        console.print(table)

    def _filter(self, actual_filter: dict[str, str | date], console: Console) -> None:
        st_date = actual_filter["st_date"]
        end_date = actual_filter["end_date"]
        show_sec = actual_filter["show_sec"]
        currency = actual_filter["currency"]

        console.print("\n[yellow]Filter[/]")

        while True:
            if show_sec:
                console.print(
                    "\nFilter by: [bold green]d[/]ate, [bold green]c[/]hange currency, "
                    "[bold green]h[/]ide Subcategory, [bold green]e[/]nd"
                )
                choice = Prompt.ask("Choice", choices=["d", "c", "h", "e"], default="d")
            else:
                console.print(
                    "\nFilter by: [bold green]d[/]ate, [bold green]c[/]hange currency, "
                    "[bold green]s[/]how Subcategory, [bold green]e[/]nd"
                )
                choice = Prompt.ask("Choice", choices=["d", "s", "h", "e"], default="d")

            if choice == "d":
                while True:
                    starting_date = Prompt.ask("Select starting date (eg 2025-01-31)")
                    ending_date = Prompt.ask("Select ending date (eg 2025-12-31)")

                    try:
                        st_date = date.fromisoformat(starting_date)
                        end_date = date.fromisoformat(ending_date)

                        if st_date > end_date:
                            console.print("[red]Try again[/]")
                            continue
                        break
                    except Exception:
                        console.print("[red]Try again[/]")
                        continue

            elif choice == "c":
                if not self.curr_list:
                    console.print(
                        "[bold red]You don't have any saved currency. "
                        "Please add them from the setting section[/bold red]"
                    )
                    Prompt.ask("")
                    break

                curr_list = [curr[0] for curr in self.curr_list]
                currency = Prompt.ask("Currency", choices=curr_list, default=self.default_currency)
                # If the default currency has not been defined, self.default_currency = None
                # and it will not be printed.

            elif choice == "h":
                show_sec = False
            elif choice == "s":
                show_sec = True

            elif choice == "e":
                filters = {
                    "st_date": st_date,
                    "end_date": end_date,
                    "currency": currency,
                    "show_sec": show_sec,
                }

                return filters

            filters = {
                "st_date": st_date,
                "end_date": end_date,
                "currency": currency,
                "show_sec": show_sec,
            }
