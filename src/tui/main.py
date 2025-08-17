import datetime
from dataclasses import dataclass

# --- Placeholder Core & Infrastructure (In your real app, you'd import these) ---


@dataclass
class Transaction:
    """A simplified domain object for this example."""

    name: str
    amount: float
    date: datetime.date


class TransactionService:
    """A placeholder service class."""

    def get_all_transactions(self):
        """Simulates fetching data from the database."""
        print("\n-- (Calling TransactionService.get_all_transactions) --")
        # In a real app, this would query the database via a repository.
        return [
            Transaction("Coffee", -3.50, datetime.date(2025, 8, 7)),
            Transaction("Salary", 2500.00, datetime.date(2025, 8, 1)),
            Transaction("Groceries", -75.25, datetime.date(2025, 8, 5)),
        ]

    def add_transaction(self, name: str, amount: float):
        """Simulates adding a new transaction."""
        print(f"\n-- (Calling TransactionService.add_transaction with '{name}', {amount}) --")
        # In a real app, this would create a Transaction object and save it.
        new_transaction = Transaction(name, amount, datetime.date.today())
        print(f"Successfully added: {new_transaction}")
        return new_transaction


# --- TUI Application ---


class TUIApp:
    def __init__(self, transaction_service: TransactionService):
        self.service = transaction_service
        self.running = True

    def run(self):
        """Starts the main command loop."""
        print("--- MoneyTracker TUI ---")
        while self.running:
            self._print_menu()
            choice = input("> ").strip().lower()
            self._handle_choice(choice)

    def _print_menu(self):
        """Displays the main menu options."""
        print("\n1. List all transactions")
        print("2. Add a new transaction")
        print("q. Quit")

    def _handle_choice(self, choice: str):
        """Processes the user's menu selection."""
        if choice == "1":
            self._list_transactions()
        elif choice == "2":
            self._add_transaction()
        elif choice == "q":
            self.running = False
            print("Goodbye!")
        else:
            print("Invalid option. Please try again.")

    def _list_transactions(self):
        """Fetches and displays all transactions."""
        transactions = self.service.get_all_transactions()
        if not transactions:
            print("No transactions found.")
            return
        print("\n--- All Transactions ---")
        for t in transactions:
            print(f"{t.date} | {t.name:<20} | {t.amount:8.2f}")
        print("------------------------")

    def _add_transaction(self):
        """Guides the user through adding a new transaction."""
        print("\n--- Add New Transaction ---")
        try:
            name = input("Name: ").strip()
            if not name:
                print("Name cannot be empty.")
                return

            amount_str = input("Amount: ").strip()
            amount = float(amount_str)

            self.service.add_transaction(name, amount)

        except ValueError:
            print("Invalid amount. Please enter a number (e.g., -25.50).")
        except Exception as e:
            print(f"An error occurred: {e}")


if __name__ == "__main__":
    # 1. Initialize your services (this is where you'd set up the UoW)
    transaction_service = TransactionService()

    # 2. Create and run the TUI app
    app = TUIApp(transaction_service)
    app.run()


# Add this to the main.py script used as the entry point of the application

# /main.py
# import sys
# import subprocess
#
# if __name__ == "__main__":
#     if len(sys.argv) > 1 and sys.argv[1] == '--tui':
#         # Run the TUI directly in the current terminal
#         subprocess.run(["python", "src/tui/main.py"])
#     else:
#         # Default to running the graphical UI and its backend
#         print("Starting backend server...")
#         subprocess.Popen(["python", "src/api/main.py"])
#
#         print("Starting graphical UI...")
#         subprocess.Popen(["python", "src/ui/main.py"])
