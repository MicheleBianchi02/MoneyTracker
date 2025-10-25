from datetime import date

from rich.console import Console
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

from moneytracker.core.domain.category import CategoryIn, CategoryOut
from moneytracker.core.exceptions import (
    OperationNotPermittedError,
    ServiceDuplicateCategoryError,
    ServiceError,
)
from moneytracker.core.services.category_service import CategoryService
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

active_tab = CATEGORY_TAB

cat_service = CategoryService()


class CategoryPage(Page):
    def __init__(self, id_user: int) -> None:
        self.id_user = id_user

    def show(self, console: Console) -> str:
        filters = {}
        filters["year"] = date.today().year
        filters["show_id"] = False
        filters["cat_type"] = "both"

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
                self._add(console)
            elif choice == "e":
                self._edit(filters, console)
            elif choice == "d":
                self._delete(filters, console)
            elif choice == "c":
                console.print(
                    "\nTabs: [bold green]d[/]ashboard, [bold green]e[/]xpense, "
                    "[bold green]i[/]ncome,  [bold green]s[/]ettings"
                )
                choice = Prompt.ask("Which Tab", choices=["d", "e", "i", "s"], default="d")

                if choice == "d":
                    return DASHBOARD_TAB

                if choice == "e":
                    return EXPENSE_TAB

                elif choice == "i":
                    return INCOME_TAB

                elif choice == "s":
                    return SETTING_TAB

            elif choice == "f":
                filters = self._filter(filters, console)

    def _draw_table(self, filters, console: Console) -> None:
        show_id = filters["show_id"]
        year = filters["year"]
        cat_type = filters["cat_type"]
        cat_type = cat_type if cat_type != "both" else None

        console.print(year)

        table_expe = Table(title="EXPENSE", show_header=True, header_style="bold magenta")
        if show_id:
            table_expe.add_column("id")
        table_expe.add_column("Category")
        table_expe.add_column("Subcategory")

        table_inc = Table(title="INCOME", show_header=True, header_style="bold magenta")
        if show_id:
            table_inc.add_column("id")
        table_inc.add_column("Category")

        cat_list = []
        with manage_uow() as uow:
            if cat_type is None:
                show_expe = True
                show_inc = True
            elif cat_type == "expense":
                show_expe = True
                show_inc = False
            elif cat_type == "income":
                show_expe = False
                show_inc = True

            if show_expe:
                prim_list = cat_service.get_primary_list(uow, self.id_user, year, "expense")
                cat_list.extend(prim_list)
                for prim in prim_list:
                    row = []
                    if show_id:
                        row.append(str(prim.id_primary))

                    row.append(prim.primary)
                    row.append("")

                    table_expe.add_row(*row, style="on blue")

                    sec_list = cat_service.get_secondary_list(uow, self.id_user, year, prim.primary)
                    cat_list.extend(sec_list)

                    for sec in sec_list:
                        row = []
                        if show_id:
                            row.append(str(sec.id_secondary))

                        row.append("")
                        row.append(sec.secondary)

                        table_expe.add_row(*row)

            if show_inc:
                prim_list = cat_service.get_primary_list(uow, self.id_user, year, "income")
                cat_list.extend(prim_list)
                for prim in prim_list:
                    row = []
                    if show_id:
                        row.append(str(prim.id_primary))

                    row.append(prim.primary)

                    table_inc.add_row(*row, style="on yellow")

        if show_expe:
            console.print(table_expe)
        if show_inc:
            console.print(table_inc)

        console.print()  # leave some space

        return cat_list

    def _add(self, console: Console) -> None:
        console.print("\n[yellow]Add Category[/]")

        while True:
            cat_type = Prompt.ask(
                "Category type: [bold green]e[/]xpense or [bold green]i[/]ncome", choices=["e", "i"]
            )
            if cat_type == "e":
                cat_type = "expense"
            else:
                cat_type = "income"

            year = IntPrompt.ask("Year", default=date.today().year)

            while True:
                primary = Prompt.ask("Category")

                if primary == "":
                    console.print("[red]The category name can't be blank[/]")
                    continue
                else:
                    break

            if cat_type == "expense":
                secondary = Prompt.ask(
                    "Subcategory (leave empty to add only the category)", default=""
                )

                if secondary == "":
                    secondary = None

            else:
                secondary = None

            cat = CategoryIn(
                year=year,
                category_type=cat_type,
                primary=primary,
                secondary=secondary,
            )

            console.print("\nNew Category:")
            console.print(f"Type: {cat_type}")
            console.print(f"Year: {year}")
            console.print(f"Category: {primary}")
            if cat_type == "expense":
                # print even if it is None
                console.print(f"Subcategory: {secondary}")

            is_ok = Confirm.ask("\nDo you want to add it?")

            if is_ok:
                try:
                    with manage_uow() as uow:
                        cat_service.add_category(uow, self.id_user, cat)
                except ServiceDuplicateCategoryError:
                    console.print("[red]Category already present[/]")
                    Prompt.ask("")
                    return

                except ServiceError:
                    console.print("[red]An error occoured, please try again[/]")
                    Prompt.ask("")
                    return

                console.print("[green]Category added successfully[/]")
            else:
                console.print("[red]Operation canceled[/]")

            Prompt.ask("")
            return

    def _edit(self, filters, console: Console) -> None:
        filters = filters.copy()
        filters["show_id"] = True

        clear_screen()
        draw_navigation_tab(active_tab, console)

        console.print("\n[yellow]Edit Category[/]")
        cat_list: list[CategoryOut] = self._draw_table(filters, console)

        id_list = []
        for cat in cat_list:
            if cat.id_primary not in id_list:
                id_list.append(cat.id_primary)
            if cat.id_secondary not in id_list and cat.id_secondary is not None:
                id_list.append(cat.id_secondary)

        while True:
            id_cat = IntPrompt.ask("id of the category to be modified")

            for cat in cat_list:
                if id_cat == cat.id_primary or id_cat == cat.id_secondary:
                    break
            else:
                # enter if break is not called. ie the id is not present

                console.print("[red]This id is not present in the table above[/]")
                Prompt.ask("")
                continue

            if cat.id_secondary is not None:
                new_name = Prompt.ask("New subcategory name")
            else:
                new_name = Prompt.ask("New category name")

            console.print("\nEdited category:")

            if cat.id_secondary is None:
                # it is a primary
                console.print(f"Category: {cat.primary} -> {new_name}")

                if cat.category_type == "expense":
                    console.print("Sub-category: -")

            else:
                console.print(f"Category: {cat.primary}")
                console.print(f"Sub-category: {cat.secondary} -> {new_name}")

            console.print(f"Year: {cat.year}")
            console.print(f"Type: {cat.category_type}")

            is_ok = Confirm.ask("\nDo you want to edit it?")

            if is_ok:
                with manage_uow() as uow:
                    try:
                        cat_service.edit(uow, id_cat, new_name, self.id_user)
                    except OperationNotPermittedError:
                        # if new_name = ""
                        console.print("[red]This is not a valid name, please try again[/]")
                        Prompt.ask("")
                        return
                    except ServiceDuplicateCategoryError:
                        console.print("[red]This name already exist, please try again[/]")
                        Prompt.ask("")
                        return
                console.print("[green]Category successfully modified[/]")

            else:
                console.print("[red]Operation canceled[/]")

            Prompt.ask("")
            return

    def _delete(self, filters, console: Console) -> None:
        filters = filters.copy()
        filters["show_id"] = True

        clear_screen()

        console.print("\n[yellow]Delete Category[/]")
        cat_list = self._draw_table(filters, console)

        while True:
            id_cat = IntPrompt.ask("id of the category to be modified")

            for cat in cat_list:
                if id_cat == cat.id_primary or id_cat == cat.id_secondary:
                    break
            else:
                # enter if break is not called. ie the id is not present

                console.print("[red]This id is not present in the table above[/]")
                Prompt.ask("")
                continue

            console.print("\nCategory to be deleted:")

            if cat.id_secondary is None:
                # it is a primary
                console.print(f"Category: {cat.primary}")

                if cat.category_type == "expense":
                    console.print("Sub-category: -")

            else:
                console.print(f"Category: {cat.primary}")
                console.print(f"Sub-category: {cat.secondary}")

            console.print(f"Year: {cat.year}")
            console.print(f"Type: {cat.category_type}")

            is_ok = Confirm.ask("\nDo you want to delete it?")

            if is_ok:
                with manage_uow() as uow:
                    try:
                        tr_list = cat_service.delete(uow, id_cat, self.id_user)
                    except OperationNotPermittedError:
                        # if new_name = ""
                        console.print(
                            "[red]It is not possible to delete category with existing sub-categories[/]"
                        )
                        Prompt.ask("")
                        return

                if tr_list:
                    n_tr = len(tr_list)
                    if n_tr == 1:
                        console.print(
                            "[red]There is one transaction pertaining to this category\n"
                            "Please edit/delete it before deleting this category.[/]"
                        )
                    else:
                        console.print(
                            f"[red]There are {n_tr} transactions pertaining to this category\n"
                            "Please edit/delete them before deleting this category.[/]"
                        )

                else:
                    console.print("[green]Category successfully deleted[/]")

            else:
                console.print("[red]Operation canceled[/]")

            Prompt.ask("")
            return

    def _filter(self, actual_filter: dict[str, str | date], console: Console) -> None:
        year = actual_filter["year"]
        show_id = actual_filter["show_id"]
        cat_type = actual_filter["cat_type"]

        console.print("\n[yellow]Filter[/]")

        while True:
            console.print(
                "\nFilter by: [bold green]y[/]ear, [bold green]t[/]ype, [bold green]e[/]nd"
            )
            choice = Prompt.ask("Choice", choices=["y", "t", "e"], default="y")

            if choice == "y":
                year = IntPrompt.ask("Select year", default=date.today().year)

            if choice == "t":
                console.print(
                    "Type: [bold green]i[/]ncome, [bold green]e[/]xpense, [bold green]b[/]oth"
                )
                choice = Prompt.ask("Type", choices=["i", "e", "b"])

                if choice == "e":
                    cat_type = "expense"
                elif choice == "i":
                    cat_type = "income"
                else:
                    cat_type = "both"

            if choice == "e":
                filters = {
                    "year": year,
                    "show_id": show_id,
                    "cat_type": cat_type,
                }
                return filters
