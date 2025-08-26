from rich.console import Console
from rich.prompt import Prompt
from rich.tree import Tree

from src.core.exceptions import ServiceError, UsernameAlreadyPresentError
from src.core.services.user_service import UserService
from src.core.services.user_setting_service import UserSettingService
from src.default_settings import DEFAULT_CURRENCY_NAME
from src.infrastructure.dependencies import get_uow
from src.tui.pages.dashboard_tab import DashboardPage
from src.tui.utils import Page, clear_screen


class SignUpPage(Page):
    def show(self, console: Console) -> Page:
        user_service = UserService()
        setting_service = UserSettingService()

        pass_equal = True
        username_not_valid = False
        error_occoured = False
        while True:
            clear_screen()

            console.print("[bold cyan]--- Sign Up ---[/bold cyan]")

            if not pass_equal:
                console.print("[red]Password don't correspond[/red]")

            if username_not_valid:
                console.print("[red]Username already in use[/red]")

            if error_occoured:
                console.print(
                    "[red]A problem occoured while signing up. Please try again[/red]",
                )

            username = Prompt.ask("Enter a new username")
            password = Prompt.ask("Enter a password", password=True)
            repeated_pass = Prompt.ask("Confirm password", password=True)

            if password != repeated_pass:
                pass_equal = False
                continue

            else:
                pass_equal = True

            # --- Services
            try:
                id_user = user_service.add(get_uow(), username, password)
            except UsernameAlreadyPresentError:
                username_not_valid = True
                continue
            except ServiceError:
                error_occoured = True
                continue

            try:
                setting_list = setting_service.get(get_uow(), None, "language")
                language_list = setting_list[0].allowed_settings
                language_list = [sett["item_value"] for sett in language_list]
                language = Prompt.ask(
                    "Enter your preferred language", choices=language_list, default="it"
                )

                available_curr = setting_service.get_currency_list(get_uow(), None)
                curr_code = [curr[0] for curr in available_curr]
                default_currency = Prompt.ask(
                    "\nEnter your preferred currency", choices=curr_code, default="EUR"
                )

                setting_service.add(get_uow(), id_user, DEFAULT_CURRENCY_NAME, default_currency)
                setting_service.add(get_uow(), id_user, "language", language)

                for curr in available_curr:
                    if curr[0] == default_currency:
                        setting_service.add_currency(get_uow(), id_user, default_currency, curr[1])
                        break

                return Tutorial(id_user)

            except ServiceError:
                # Even if the settings are not added because a probelm occoured.
                # The default settings will be used. The user will update them later
                # from the settin.

                return Tutorial(id_user)


class Tutorial(Page):
    def __init__(self, id_user: int) -> None:
        self.id_user = id_user

    def show(self, console: Console) -> Page:
        clear_screen()

        console.print("[bold cyan]--- Signed In ---[/bold cyan]")
        console.print("\nTransactions can have different categories depending on the type.")
        console.print("For expenses there are categories and subcategories.")
        console.print("Both can be used for categorizing transactions.")
        console.print("Subcategories are optional")
        console.print("\nExample are:")

        expe_1 = Tree("Leisure")
        expe_1.add("Cinema")
        expe_1.add("Going Out")
        expe_1.add("Trip")

        expe_2 = Tree("Transport")
        expe_2.add("Train")
        expe_2.add("Car")

        console.print(expe_1)
        console.print("Health")
        console.print(expe_2)

        console.print("\nIncome doesn't support subcategories")

        console.print(
            "\nCategories are valid for a year, next they need to be redefined. "
            "This enable you to add categories only when they are really necessary "
            "(for example, cinema is you new passion, it not usefull to add that "
            "subcategory to the previous years.)"
        )

        Prompt.ask(":[blue]---------------------------[/]")

        console.print(
            "Multiple currencies are available at any time. To enable them look at the settings."
        )

        Prompt.ask(":[blue]---------------------------[/]")

        return DashboardPage(self.id_user)
