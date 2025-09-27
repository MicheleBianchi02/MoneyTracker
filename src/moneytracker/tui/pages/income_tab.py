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
    CATEGORY_TAB,
    DASHBOARD_TAB,
    EXPENSE_TAB,
    INCOME_TAB,
    SETTING_TAB,
    Page,
    clear_screen,
    draw_navigation_tab,
)
from moneytracker.utils import format_value

active_tab = INCOME_TAB


tr_service = TransactionService()
setting_service = UserSettingService()
cat_service = CategoryService()

# None replacement for keys in the returned dictionary
none_key = NONE_REPLACEMENT


class IncomePage(Page):
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
                    "\nTabs: [bold green]d[/]ashboard, [bold green]e[/]xpense, "
                    "[bold green]c[/]ategory, [bold green]s[/]ettings"
                )
                choice = Prompt.ask("Which Tab", choices=["d", "e", "c", "s"], default="d")

                if choice == "d":
                    return DASHBOARD_TAB

                elif choice == "e":
                    return EXPENSE_TAB

                elif choice == "c":
                    return CATEGORY_TAB

                elif choice == "s":
                    return SETTING_TAB

            elif choice == "f":
                filters = self._filter(filters, console)

    def _draw_table(
        self,
        filters: dict[str, str | date | bool],
        console: Console,
    ) -> None:
        st_date = filters["st_date"]
        end_date = filters["end_date"]
        currency = filters["currency"]

        with manage_uow() as uow:
            prim_list = []

            year = st_date.year
            while year <= end_date.year:
                cat_list = cat_service.get_primary_list(uow, self.id_user, year, "income")

                prim_list.append(cat_list)

                year += 1

            summary, is_valid = tr_service.get_summary(
                uow,
                self.id_user,
                st_date,
                end_date,
                "income",
                currency,
                None,
                None,
            )

        table = Table()
        table.add_column("Category")
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
            prim_row = [0] * 14
            prim_row[0] = prim
            for sum_date, value in res[none_key].items():
                # There can be multiple years, so we have to sum the months
                month = int(sum_date[5:])
                prim_row[month] += value

            rows.append(prim_row)

        for cat in cat_list:
            if cat.primary not in summary:
                prim_row = [0] * 14
                prim_row[0] = cat.primary

                rows.append(prim_row)

        total_row = [0] * 14
        total_row[0] = "Total"
        for row in rows:
            row[-1] = sum(row[1:])  # right Total
            for idx, val in enumerate(row[1:]):
                total_row[idx + 1] += val

            row[1:] = [format_value(par, self.value_format) for par in row[1:]]
            table.add_row(*row, style="on blue")

        table.add_row("")

        total_row[1:] = [format_value(par, self.value_format) for par in total_row[1:]]
        table.add_row(*total_row, style="on green")

        info = st_date.isoformat() + " -> " + end_date.isoformat()
        info += f" , currency: {currency}"

        console.print(info)

        console.print(table)

        if not is_valid:
            console.print("[yellow]\u26a0 Some currency conversion rates are not up to date[/]")

    def _filter(self, actual_filter: dict[str, str | date], console: Console) -> None:
        st_date = actual_filter["st_date"]
        end_date = actual_filter["end_date"]
        currency = actual_filter["currency"]

        console.print("\n[yellow]Filter[/]")

        while True:
            console.print(
                "\nFilter by: [bold green]d[/]ate, [bold green]c[/]hange currency, "
                "[bold green]e[/]nd"
            )
            choice = Prompt.ask("Choice", choices=["d", "c", "e"], default="d")

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

            elif choice == "e":
                filters = {
                    "st_date": st_date,
                    "end_date": end_date,
                    "currency": currency,
                }

                return filters

            filters = {
                "st_date": st_date,
                "end_date": end_date,
                "currency": currency,
            }
