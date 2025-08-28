import time

from rich.console import Console
from rich.prompt import Prompt

from src.core.services.user_service import UserService
from src.infrastructure.dependencies import get_uow
from src.tui.pages.menu import MenuPage
from src.tui.pages.sign_up import SignUpPage
from src.tui.utils import DASHBOARD_TAB, Page, clear_screen

user_service = UserService()


class LoginPage(Page):
    def show(self, console: Console) -> Page:
        first = True
        is_auth = False

        while not is_auth:
            clear_screen()

            console.print("[bold cyan]--- Welcome ---[/bold cyan]")

            console.print("1. Login")
            console.print("2. Sign Up")
            console.print("[yellow]q. Quit[/yellow]")

            if not first:
                console.print("[red]Wrong username or password[/red]")
            else:
                first = False

            choice = Prompt.ask("\nEnter your choice", choices=["1", "2", "q"], default="1")

            if choice == "1":
                console.print("\n--- Login ---")

                username = Prompt.ask("Username")
                password = Prompt.ask("Password", password=True)

                is_auth, id_user = user_service.authenticate(get_uow(), username, password)

                if is_auth:
                    return MenuPage(id_user, DASHBOARD_TAB)

            elif choice == "2":
                return SignUpPage()

            elif choice == "q":
                console.print("[bold red]Exiting...[/bold red]")
                time.sleep(0.5)
                return None
