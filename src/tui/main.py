from rich.console import Console

from src.core.services.startup import bootstrap_app, startup
from src.tui.pages.login import LoginPage

ENTER_ALT_SCREEN = "\x1b[?1049h"
EXIT_ALT_SCREEN = "\x1b[?1049l"


def main():
    console = Console()

    current_page = LoginPage()
    while current_page is not None:
        current_page = current_page.show(console)


if __name__ == "__main__":
    bootstrap_app()
    startup()

    try:
        print(ENTER_ALT_SCREEN)
        main()
    except (KeyboardInterrupt, EOFError):
        # Handle Ctrl+C or Ctrl+D gracefully
        print("\nExiting...")

    finally:
        print(EXIT_ALT_SCREEN)
