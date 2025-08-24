from rich.console import Console
from rich.prompt import Prompt

from src.core.services.user_service import UserService
from src.core.services.user_setting_service import UserSettingService
from src.infrastructure.dependencies import get_uow
from src.tui.utils import Page, clear_screen


class SignUpPage(Page):
    def show(self, console: Console) -> Page:
        user_service = UserService()
        setting_service = UserSettingService()

        pass_equal = True
        while True:
            clear_screen()

            console.print("[bold cyan]--- Sign Up ---[/bold cyan]")

            if not pass_equal:
                console.print("[red]Password don't correspond[/red]")

            username = Prompt.ask("Enter a new username")
            password = Prompt.ask("Enter a password", password=True)
            repeated_pass = Prompt.ask("Confirm password", password=True)

            if password != repeated_pass:
                pass_equal = False
                continue

            else:
                pass_equal = True

            setting_list = setting_service.get(get_uow(), None, "language")
            language_list = setting_list[0].allowed_settings
            language_list = [sett["item_value"] for sett in language_list]
            language = Prompt.ask("Enter your preferred language", choices=language_list)

            available_curr = setting_service.get_currency_list(get_uow(), None)
            default_currency = Prompt.ask("\nEnter your preferred currency", choices=available_curr)

            id_user = user_service.add(get_uow(), username, password)
            setting_service.add(get_uow(), id_user, "default_currency", default_currency)
            setting_service.add(get_uow(), id_user, "language", language)

            setting_service.add_currency(get_uow(), id_user, default_currency)
