from rich.console import Console

from moneytracker.tui.pages.login import LoginPage
from moneytracker.tui.pages.setting import ALTERNATE_SCREEN_MODE
from moneytracker.tui.utils import clear_screen

ENTER_ALT_SCREEN = "\x1b[?1049h"
EXIT_ALT_SCREEN = "\x1b[?1049l"


def run_tui(mode: str) -> None:
    try:
        if mode == ALTERNATE_SCREEN_MODE:
            print(ENTER_ALT_SCREEN)

        console = Console()

        current_page = LoginPage()
        while current_page is not None:
            current_page = current_page.show(console)

        clear_screen()
    except (KeyboardInterrupt, EOFError):
        # Handle Ctrl+C or Ctrl+D gracefully
        print("\nExiting...")

    finally:
        if mode == ALTERNATE_SCREEN_MODE:
            print(EXIT_ALT_SCREEN)
