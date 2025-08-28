import argparse

from rich.console import Console

from src.core.services.startup import bootstrap_app, startup
from src.tui.pages.login import LoginPage
from src.tui.utils import clear_screen

ENTER_ALT_SCREEN = "\x1b[?1049h"
EXIT_ALT_SCREEN = "\x1b[?1049l"


def main():
    console = Console()

    current_page = LoginPage()
    while current_page is not None:
        current_page = current_page.show(console)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Personal Finance Application")
    parser.add_argument("-d", action="store_true", help="Open in delete screen mode")
    parser.add_argument("-a", action="store_true", help="Open in alternate screen mode")
    args = parser.parse_args()

    bootstrap_app()
    startup()

    try:
        if args.a:
            print(ENTER_ALT_SCREEN)
        main()
    except (KeyboardInterrupt, EOFError):
        # Handle Ctrl+C or Ctrl+D gracefully
        print("\nExiting...")

    finally:
        if args.a:
            print(EXIT_ALT_SCREEN)

        else:
            clear_screen()
