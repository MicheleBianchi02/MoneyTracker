import calendar
from datetime import date

from rich.console import Console
from rich.prompt import Confirm, FloatPrompt, IntPrompt, Prompt
from rich.table import Table

from src.core.domain.transaction import TransactionIn, TransactionOut
from src.core.exceptions import ServiceError
from src.core.services.category_service import CategoryService
from src.core.services.transaction_service import TransactionService
from src.core.services.user_setting_service import UserSettingService
from src.default_settings import DEFAULT_CURRENCY_NAME
from src.infrastructure.dependencies import get_uow
from src.tui.pages.expense_tab import ExpensePage
from src.tui.utils import DASHBOARD_TAB, Page, clear_screen, draw_navigation_tab
from src.utils import format_value

active_tab = DASHBOARD_TAB

tr_service = TransactionService()
setting_service = UserSettingService()
cat_service = CategoryService()


class DashboardPage(Page):
    def __init__(self, id_user: int) -> None:
        self.id_user = id_user

        setting = setting_service.get(get_uow(), id_user, "value_format")[0]
        self.value_format = setting.value

        # code used to dissplay all cat in the filter
        self._cat_code = "ncsk8swedmsf402323"

        self.curr_list = setting_service.get_currency_list(get_uow(), self.id_user)
        self.default_currency = setting_service.get(get_uow(), self.id_user, DEFAULT_CURRENCY_NAME)

        if not self.default_currency:
            self.default_currency = None
        else:
            self.default_currency = self.default_currency[0].value

    def show(self, console: Console) -> Page:
        year = date.today().year
        month = date.today().month

        last_day = calendar.monthrange(year, month)[1]
        st_date = date(year, month, 1)
        end_date = date(year, month, last_day)

        filters = {
            "st_date": st_date,
            "end_date": end_date,
            "type": "both",
            "primary": self._cat_code,
            "secondary": None,
            "show_id": False,
        }

        while True:
            clear_screen()

            draw_navigation_tab(active_tab, console)

            self._draw_table(filters, console)

            console.print(
                "\nAction: [bold green]a[/]dd, [bold green]e[/]dit, [bold green]d[/]elete, "
                "[bold green]c[/]hange tab, [bold green]f[/]ilter,  [bold green]q[/]uit"
            )

            choice = Prompt.ask("Choice", choices=["a", "e", "d", "c", "f", "q"], default="c")

            if choice == "q":
                return None

            elif choice == "a":
                self._add_tr(console)

            elif choice == "e":
                self._edit_tr(filters, console)

            elif choice == "d":
                self._delete_tr(filters, console)

            elif choice == "c":
                console.print(
                    "\nTabs: [bold green]e[/]xpense, [bold green]i[/]ncome, "
                    "[bold green]c[/]ategory, [bold green]s[/]ettings"
                )
                choice = Prompt.ask("Which Tab", choices=["e", "i", "c", "s"], default="e")

                return ExpensePage()

            elif choice == "f":
                filters = self._filter(filters, console)

    def _draw_table(
        self,
        filters: dict[str, str | date],
        console: Console,
    ) -> list[TransactionOut]:
        st_date = filters["st_date"]
        end_date = filters["end_date"]
        tr_type = filters["type"]
        primary = filters["primary"]
        secondary = filters["secondary"]
        show_id = filters["show_id"]

        month_column = False
        year_column = False

        if st_date.year != end_date.year:
            month_column = True
            year_column = True

        else:
            if st_date.month != end_date.month:
                month_column = True

        cat_type = tr_type if tr_type != "both" else None

        if primary == self._cat_code:
            primary = None
            secondary = None

        tr_list = tr_service.get_transaction(
            get_uow(),
            self.id_user,
            st_date,
            end_date,
            tr_type=cat_type,
            primary=primary,
            secondary=secondary,
        )

        table = Table(show_header=True, header_style="bold magenta")

        if show_id:
            table.add_column("id")
        if year_column:
            table.add_column("year")
        if month_column:
            table.add_column("month")
        table.add_column("day")
        table.add_column("category")
        table.add_column("name")
        table.add_column("value")
        table.add_column("currency")
        table.add_column("description")

        # TODO: In this way we are not considering the different currencies
        total_expe = 0
        total_inc = 0
        balance = 0
        for tr in tr_list:
            if tr.tr_type == "expense":
                total_expe += tr.value
                balance -= tr.value
            else:
                balance += tr.value
                total_inc += tr.value

            if tr.tr_type == "expense":
                value = "[red]-[/]" + format_value(tr.value, self.value_format)

            else:
                value = "[green]+[/]" + format_value(tr.value, self.value_format)

            category = tr.secondary if tr.secondary is not None else tr.primary

            parameters = []
            if show_id:
                parameters.append(str(tr.id))

            parameters.append(str(tr.tr_date.day))

            if year_column:
                parameters.append(str(tr.tr_date.year))

            if month_column:
                parameters.append(str(tr.tr_date.month))

            parameters.extend(
                [
                    category,
                    tr.name,
                    value,
                    tr.currency,
                    tr.description,
                ]
            )

            table.add_row(*parameters)

        info = st_date.isoformat() + " -> " + end_date.isoformat()

        if tr_type == "both":
            info += " , expense & income"
        else:
            info += f" , {tr_type}"

        if category == self._cat_code:
            info += " , all categories"

        else:
            if secondary is None and primary is not None:
                info += f" , {primary}"

            elif primary is not None:
                info += f" , {primary}-{secondary}"

        console.print(info)
        console.print(table)

        total_inc = format_value(total_inc, self.value_format)
        total_expe = format_value(total_expe, self.value_format)
        console.print(f"Total income: [green]+[/]{total_inc} {self.default_currency}")
        console.print(f"Total expenses: [red]-[/]{total_expe} {self.default_currency}")

        bal = abs(balance)
        bal = format_value(bal, self.value_format)
        if balance < 0:
            console.print(f"Balance: [red]-[/]{bal} {self.default_currency}")
        elif balance > 0:
            console.print(f"Balance: [green]-[/]{bal} {self.default_currency}")
        else:
            console.print(f"Balance: {bal} {self.default_currency}")
        return tr_list

    def _filter(self, actual_filter: dict[str, str | date], console: Console) -> None:
        st_date = actual_filter["st_date"]
        end_date = actual_filter["end_date"]
        tr_type = actual_filter["type"]
        primary = actual_filter["primary"]
        secondary = actual_filter["secondary"]
        show_id = actual_filter["show_id"]

        console.print("\n[yellow]Filter[/]")

        while True:
            console.print(
                "\nFilter by: [bold green]d[/]ate, [bold green]t[/]ype, "
                "[bold green]c[/]ategory, [bold green]e[/]nd"
            )
            choice = Prompt.ask("Choice", choices=["d", "t", "c", "e"], default="d")

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

            elif choice == "t":
                console.print(
                    "Type: [bold green]i[/]ncome, [bold green]e[/]xpense, [bold green]b[/]oth"
                )
                choice = Prompt.ask("Type", choices=["i", "e", "b"])

                if choice == "e":
                    tr_type = "expense"
                elif choice == "i":
                    tr_type = "income"
                else:
                    tr_type = "both"

            elif choice == "c":
                year_list = []
                tr_date = st_date
                while tr_date < end_date:
                    year_list.append(tr_date.year)

                    tr_date = tr_date.replace(year=tr_date.year + 1)

                if tr_type == "income":
                    cat_list = []
                    for year in year_list:
                        cat_list.extend(
                            cat_service.get_primary_list(get_uow(), self.id_user, year, "income")
                        )

                    prim_name = [cat.primary for cat in cat_list]
                    prim_name = set(prim_name)
                    choice = Prompt.ask(
                        "Category (leave empty to show all)", choices=prim_name, default=""
                    )

                    if choice == "":
                        primary = self._cat_code
                    else:
                        primary = choice

                    secondary = None

                elif tr_type == "expense":
                    prim_list = []
                    for year in year_list:
                        prim_list.extend(
                            cat_service.get_primary_list(
                                get_uow(),
                                self.id_user,
                                year,
                                "expense",
                            )
                        )

                    prim_name = [cat.primary for cat in prim_list]
                    prim_name = set(prim_name)
                    choice = Prompt.ask(
                        "Category (leave empty to show all)", choices=prim_name, default=""
                    )

                    if choice == "":
                        primary = self._cat_code
                        secondary = None
                    else:
                        primary = choice

                        sec_list = []
                        for year in year_list:
                            sec_list.extend(
                                cat_service.get_secondary_list(
                                    get_uow(), self.id_user, year, primary
                                )
                            )

                        sec_name = [cat.secondary for cat in sec_list]
                        sec_name = set(sec_name)
                        choice = Prompt.ask(
                            "Subcategory (leave empty to show all)", choices=sec_name, default=""
                        )

                        if choice == "":
                            secondary = None
                        else:
                            secondary = choice

                elif tr_type == "both":
                    cat_list = []
                    for year in year_list:
                        cat_list.extend(
                            cat_service.get_primary_list(get_uow(), self.id_user, year, None)
                        )

                    prim_name = [cat.primary for cat in cat_list]
                    prim_name = set(prim_name)
                    choice = Prompt.ask(
                        "Category (leave empty to show all)", choices=prim_name, default=""
                    )

                    if choice == "":
                        primary = self._cat_code
                        secondary = None

                    else:
                        primary = choice
                        for cat in cat_list:
                            if primary == cat.primary:
                                tr_type = cat.category_type

                                if tr_type == "expense":
                                    sec_list = []
                                    for year in year_list:
                                        sec_list.extend(
                                            cat_service.get_secondary_list(
                                                get_uow(), self.id_user, year, primary
                                            )
                                        )

                                    sec_name = [cat.secondary for cat in sec_list]
                                    sec_name = set(sec_name)
                                    choice = Prompt.ask(
                                        "Subcategory (leave empty to show all)",
                                        choices=sec_name,
                                        default="",
                                    )

                                    if choice == "":
                                        secondary = None
                                    else:
                                        secondary = choice

                                else:
                                    secondary = None

            elif choice == "e":
                filters = {
                    "st_date": st_date,
                    "end_date": end_date,
                    "type": tr_type,
                    "primary": primary,
                    "secondary": secondary,
                    "show_id": False,
                }

                return filters

            filters = {
                "st_date": st_date,
                "end_date": end_date,
                "type": tr_type,
                "primary": primary,
                "secondary": secondary,
                "show_id": False,
            }

    def _add_tr(self, console: Console) -> None:
        console.print("\n[yellow]Add Transaction[/]")

        while True:
            year = IntPrompt.ask("Year", default=date.today().year)
            month = IntPrompt.ask("Month", default=date.today().month)
            day = IntPrompt.ask("Day", default=date.today().day)

            try:
                tr_date = date(year, month, day)

            except Exception:
                console.print("[red]Try again[/]")
                continue

            prim_list = cat_service.get_primary_list(get_uow(), self.id_user, tr_date.year, None)
            if not prim_list:
                console.print(
                    "[bold red]You don't have any saved category. "
                    "Please add them from the setting section[/bold red]"
                )
                break

            prim_name = [cat.primary for cat in prim_list]

            primary = Prompt.ask("Category", choices=prim_name)

            for cat in prim_list:
                if primary == cat.primary:
                    tr_type = cat.category_type
                    break

            if tr_type == "income":
                secondary = None
            else:
                sec_list = cat_service.get_secondary_list(
                    get_uow(), self.id_user, tr_date.year, primary
                )

                sec_name = [cat.secondary for cat in sec_list]

                secondary = Prompt.ask(
                    "Subcategory (leave empty to use only the category)",
                    choices=sec_name,
                    default="",
                )

                if secondary == "":
                    secondary = None

            while True:
                value = FloatPrompt.ask("Value")

                if value < 0:
                    if tr_type == "expense":
                        value = abs(value)
                        break

                    else:
                        console.print("[red]Income can't be negaive[/]")
                        continue

                break

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

            name = Prompt.ask("Name")
            description = Prompt.ask("Description")

            tr = TransactionIn(
                id_user=self.id_user,
                primary=primary,
                secondary=secondary,
                tr_type=tr_type,
                tr_date=tr_date,
                name=name,
                value=value,
                currency=currency,
                description=description,
            )

            console.print("\nNew transaction:")
            console.print(f"Date: {tr_date.isoformat()}")
            console.print(f"Name: {name}")

            if tr_type == "expense":
                value = "[red]-[/]" + format_value(value, self.value_format)
            else:
                value = "[green]+[/]" + format_value(value, self.value_format)
            console.print(f"value: {value}")
            console.print(f"Currency: {currency}")
            console.print(f"Category: {primary}")
            if secondary is not None:
                console.print(f"Subcategory: {secondary}")
            console.print(f"Description: {description}")

            is_ok = Confirm.ask("\nDo you want to add it?")

            if is_ok:
                try:
                    tr_service.add_transaction(get_uow(), tr)
                except ServiceError:
                    console.print("\n[red]An error occoured, please try again[/]")
                    Prompt.ask("")
                    return
                console.print("[green]Transaction successfully added[/]")
            else:
                console.print("[red]Operation canceled[/]")

            Prompt.ask("")
            return

    def _edit_tr(self, filters, console: Console) -> None:
        filters = filters.copy()
        filters["show_id"] = True

        clear_screen()

        console.print("\n[yellow]Edit Transaction[/]")
        tr_list = self._draw_table(filters, console)

        while True:
            id_tr = IntPrompt.ask("id of the transaction to be modified")
            console.print("leave empty if it remain the same")

            for tr in tr_list:
                if id_tr == tr.id:
                    break
            else:
                # enter if break is not called. ie the id is not present

                console.print("[red]This id is not present in the table above[/]")
                Prompt.ask("")
                continue

            year = IntPrompt.ask("New year", default=tr.tr_date.year)
            month = IntPrompt.ask("New month", default=tr.tr_date.month)
            day = IntPrompt.ask("New day", default=tr.tr_date.day)

            try:
                new_date = date(year, month, day)

            except Exception:
                console.print("[red]Try again[/]")
                continue

            prim_list = cat_service.get_primary_list(get_uow(), self.id_user, year, tr.tr_type)
            if not prim_list:
                console.print("[red]There are no categories for that year.[/]")
                Prompt.ask("")
                return

            prim_name = [cat.primary for cat in prim_list]
            while True:
                primary = Prompt.ask("New Category", choices=prim_name, default=tr.primary)
                if primary not in prim_name:
                    console.print("[red]That category is not available for that year.[/]")
                    continue
                break

            if tr.tr_type == "expense":
                sec_list = cat_service.get_secondary_list(
                    get_uow(),
                    self.id_user,
                    year,
                    primary,
                )

                if sec_list:
                    sec_name = [cat.secondary for cat in sec_list]

                    secondary = Prompt.ask(
                        "New subcategory  (leave empty if you want to remove the subcategory)",
                        choices=sec_name,
                        default="",
                    )

                    if secondary == "":
                        secondary = None
            else:
                secondary = None

            value = FloatPrompt.ask("New value", default=tr.value)

            if not self.curr_list:
                console.print(
                    "[bold red]You don't have any saved currency. "
                    "Please add them from the setting section[/bold red]"
                )
                Prompt.ask("")
                break

            curr_list = [curr[0] for curr in self.curr_list]
            currency = Prompt.ask("New currency", choices=curr_list, default=tr.currency)

            name = Prompt.ask("New name", default=tr.name)
            description = Prompt.ask("New description", default=tr.description)

            new_tr = TransactionIn(
                id_user=self.id_user,
                primary=primary,
                secondary=secondary,
                tr_type=tr.tr_type,
                tr_date=new_date,
                name=name,
                value=value,
                currency=currency,
                description=description,
            )

            console.print("\nNew transaction:")
            console.print(f"Date: {tr.tr_date.isoformat()} -> {new_date.isoformat()}")
            console.print(f"Name: {name} -> {name}")

            if new_tr.tr_type == "expense":
                old_value = "[red]-[/]" + format_value(tr.value, self.value_format)
                value = "[red]-[/]" + format_value(value, self.value_format)
            else:
                old_value = "[green]+[/]" + format_value(tr.value, self.value_format)
                value = "[green]+[/]" + format_value(value, self.value_format)
            console.print(f"value: {old_value} -> {value}")
            console.print(f"Currency: {tr.currency} -> {currency}")
            console.print(f"Category: {tr.primary} -> {primary}")

            if tr.tr_type == "expense":
                if secondary is not None:
                    console.print(f"Subcategory: {tr.secondary} -> {secondary}")
                else:
                    if tr.secondary is not None:
                        console.print(f"Subcategory: {tr.secondary} -> -")
                    else:
                        console.print("Subcategory: - -> -")
            console.print(f"Description: {tr.description} -> {description}")

            is_ok = Confirm.ask("\nDo you want to edit it?")

            if is_ok:
                try:
                    tr_service.edit_transaction(get_uow(), id_tr, new_tr)
                except ServiceError:
                    console.print("\n[red]An error occoured, please try again[/]")
                    Prompt.ask("")
                    return
                console.print("[green]Transaction successfully modified[/]")
            else:
                console.print("[red]Operation canceled[/]")

            Prompt.ask("")
            return

    def _delete_tr(self, filters, console: Console) -> None:
        filters = filters.copy()
        filters["show_id"] = True

        clear_screen()

        console.print("\n[yellow]Delete Transaction[/]")
        tr_list = self._draw_table(filters, console)

        while True:
            id_tr = IntPrompt.ask("id of the transaction to be deleted")

            for tr in tr_list:
                if id_tr == tr.id:
                    break
            else:
                # enter if break is not called. ie the id is not present

                console.print("[red]This id is not present in the table above[/]")
                Prompt.ask("")
                continue

            console.print("\nTransaction:")
            console.print(f"Date: {tr.tr_date.isoformat()}")
            console.print(f"Name: {tr.name}")

            if tr.tr_type == "expense":
                value = "[red]-[/]" + format_value(tr.value, self.value_format)
            else:
                value = "[green]+[/]" + format_value(tr.value, self.value_format)
            console.print(f"value: {value}")
            console.print(f"Currency: {tr.currency}")
            console.print(f"Category: {tr.primary}")
            if tr.secondary is not None:
                console.print(f"Subcategory: {tr.secondary}")
            console.print(f"Description: {tr.description}")

            is_ok = Confirm.ask("\nDo you want to delete it?")

            if is_ok:
                try:
                    tr_service.delete_transaction(get_uow(), id_tr)
                except ServiceError:
                    console.print("\n[red]An error occoured, please try again[/]")
                    Prompt.ask("")
                    return
                console.print("[green]Transaction successfully deleted[/]")
            else:
                console.print("[red]Operation canceled[/]")

            Prompt.ask("")
            return
