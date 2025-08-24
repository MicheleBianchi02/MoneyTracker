class Page:
    def show(self):
        raise NotImplementedError


def clear_screen() -> None:
    print("\x1b[2J\x1b[H")
