# MoneyTracker

> **A powerful, privacy-first personal finance tracker with a built-in Terminal User Interface (TUI) and a REST API backend — all running locally on your machine.**

MoneyTracker gives you complete control over your financial data. It tracks your income and expenses, converts amounts across multiple currencies using live exchange rates, and presents everything through an intuitive, keyboard-driven terminal interface. No cloud, no subscriptions — just you and your finances.

---

## Key Features

- **Interactive TUI Dashboard** — A rich, keyboard-navigable terminal interface built with [Rich](https://github.com/Textualize/rich). View your current month's transactions, balance, and totals at a glance with colour-coded income (green) and expense (red) entries.
- **Multi-Currency Support** — Log transactions in any currency you choose. MoneyTracker automatically fetches daily exchange rates from the **European Central Bank (ECB)** and converts all values to your preferred reporting currency at the historic rate of the transaction date.
- **Annual Category System** — Categories are year-specific by design, reflecting how spending habits evolve over time. Income and expense categories are hierarchical: expenses support a two-level **primary / secondary (subcategory)** structure for precise tracking.
- **Pivot-Table Reporting** — The Expense and Income tabs present data as pivot tables, with categories as rows and the 12 months as columns, including row and column totals for a complete annual overview. Subcategory visibility can be toggled for high-level or detailed breakdowns.
- **Multi-User with JWT Authentication** — Each user's data is fully isolated. The API is secured with OAuth2 Bearer tokens (JWT), ensuring that users can only ever access their own records.
- **Configurable Settings** — Personalise the app with settings for default currency, number format (e.g. `1,000.00` vs `1.000,00`), language (English, Italian, French), theme, and font size.
- **Robust Backend** — Built on **FastAPI** + **SQLite** with a clean layered architecture (domain → services → repositories), a connection pool, a background job manager, and graceful startup/shutdown lifecycle hooks.
- **Currency Validation Warnings** — If an exchange rate could not be fetched for a given transaction date, the dashboard displays a clear warning (`⚠ Some currency conversion rates are not up to date`) so you always know when a total might be approximate.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python ≥ 3.12.3 |
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) |
| **TUI Rendering** | [Rich](https://github.com/Textualize/rich) |
| **Database** | SQLite (via built-in `sqlite3`) |
| **Data Validation** | [Pydantic v2](https://docs.pydantic.dev/latest/) |
| **HTTP Client** | [Requests](https://requests.readthedocs.io/) |
| **Exchange Rate Source** | European Central Bank (ECB) API |
| **Authentication** | OAuth2 + JWT (Bearer tokens) |
| **Build System** | [Hatchling](https://hatch.pypa.io/) / `pyproject.toml` |
| **Testing** | [pytest](https://pytest.org/) |

---

## Installation

### Prerequisites

- Python **3.12.3** or newer
- A virtual environment (recommended)

### Steps

1. **Clone the repository:**

   ```bash
   git clone https://github.com/MicheleBianchi02/MoneyTracker.git
   cd MoneyTracker
   ```

2. **Create and activate a virtual environment:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # On Windows: .venv\Scripts\activate
   ```

3. **Install the package in editable mode:**

   ```bash
   pip install -e .
   ```

   This installs all required dependencies (`pydantic`, `requests`, `pytest`, and the FastAPI/Uvicorn stack) automatically.

---

## Building a Release Binary

> These steps are for **developers** who want to produce a distributable binary.
> End-users should follow the [Installing from a Binary Release](#-installing-from-a-binary-release) section below.

### Prerequisites

- The project venv must be active and all dependencies installed (`pip install -e .`)
- PyInstaller must be present in the venv (it is included as a dev dependency)

### Build

```bash
./build.sh
```

The script will:
1. Clean any previous `build/` and `dist/` directories
2. Run PyInstaller using `moneytracker.spec`
3. Produce `dist/moneytracker/` — the self-contained application directory
4. Package it into `moneytracker-linux-<arch>.tar.gz` ready for upload to a GitHub Release

---

## Installing from a Binary Release

> These steps are for **end-users** who downloaded the pre-built binary from the GitHub Releases page.

1. **Download** `moneytracker-linux-x86_64.tar.gz` (or `aarch64`) from the [Releases](../../releases) page.

2. **Extract** the bundle to a permanent location (e.g. `/opt`):

   ```bash
   tar -xzf moneytracker-linux-x86_64.tar.gz -C ~/.local/
   ```

   This creates `/opt/moneytracker/` containing the executable and its bundled runtime.

3. **Create a symlink** so the command is available system-wide:

   ```bash
   sudo ln -s ~/.local/moneytracker/moneytracker /usr/local/bin/moneytracker
   ```

   > **Tip:** Use `~/.local/bin/` instead of `/usr/local/bin/` if you prefer a user-only install (no `sudo` needed). Make sure `~/.local/bin` is on your `$PATH`.

4. **Run:**

   ```bash
   moneytracker --terminal
   ```

**All user data** (database, config, logs) is stored in your home directory under the standard XDG paths — never inside the installation directory. You can safely move or update the bundle without losing any data.

| Path | Contents |
|---|---|
| `~/.local/share/MoneyTracker/` | SQLite database |
| `~/.config/MoneyTracker/` | Server settings JSON |
| `~/.local/state/MoneyTracker/` | Log files |

---

## Usage

MoneyTracker can be run in two modes: the **Terminal UI (TUI)** for interactive use, or as a **REST API server** for integration with other clients.

### Run the Terminal UI (recommended)

```bash
moneytracker --terminal
```

On first launch you will be asked to choose a display mode:

| Key | Mode | Description |
|---|---|---|
| `a` | Alternate screen | Opens a clean TUI pane; your terminal history is preserved. |
| `c` | Current window | Runs the TUI inline; terminal history above it is cleared. |

You can save your preferred mode permanently when prompted.

### Run the REST API Server only

```bash
moneytracker
```

The server starts at `http://localhost:<port>` (configured in your app settings). Interactive API documentation is available at `http://localhost:<port>/docs`.

---

## Navigating the TUI

Once logged in (or after creating an account), you will land on the main menu. Use the following controls:

| Key / Input | Action |
|---|---|
| Tab labels (`1`–`5`) | Switch between Dashboard, Expenses, Income, Categories, Settings |
| Arrow keys | Navigate tables and lists |
| `Enter` | Select / confirm |
| `a` | Add a new item (transaction, category, currency) |
| `e` | Edit the selected item |
| `d` | Delete the selected item |
| `f` | Apply a filter (date range, category, currency) |
| `q` / `Ctrl+C` | Quit / go back |

> **Tip:** The Dashboard defaults to the **current month**. Use the filter (`f`) to change the date range or currency for the report.

---

## Documentation

Additional documentation is available in the [`docs/`](docs/) directory:

- [`app_guide.md`](docs/app_guide.md) — Core concepts (Annual Categories, Multi-Currency), practical workflows, and frontend implementation insights derived from the TUI.
- [`API_docs.md`](docs/API_docs.md) — Detailed REST API reference for every endpoint.
- [`Domain.md`](docs/Domain.md) — Design notes on the domain model, exchange rate strategy, and category lifecycle.
- [`openapi.json`](docs/openapi.json) — Machine-readable OpenAPI 3.x specification (importable into Postman, Insomnia, etc.).

---

## Roadmap

The following improvements and new features are planned for future releases.

### Performance & Infrastructure

- [ ] **Rewrite performance-critical core in C** — Offload hot paths such as currency conversion and summary-table aggregation to a C extension (via `ctypes` or a Python C extension module) to significantly speed up pivot-table generation for large datasets.
- [ ] **Rename the application** — Choose and adopt a final product name across all files, configuration, and documentation.

### New Features

- [ ] **Net worth tracking** — Add backend support for asset and liability accounts (savings, investments, loans, property) to calculate and display a real-time net worth alongside the existing income/expense tracking.
- [ ] **Budgeting** — Define monthly or annual spending targets per category. Track progress against budgets in the dashboard and surface warnings when a category is approaching or has exceeded its limit.
- [ ] **Dedicated frontend** — Build a graphical user interface (desktop via Tauri, or web-based) that consumes the existing REST API, making the app accessible to users who prefer a GUI over the TUI.
- [ ] **Recurring transactions** — Define fixed periodic entries (e.g. monthly rent, annual subscriptions, regular salary) that are auto-logged on schedule, eliminating repetitive manual entry.
- [ ] **CSV / bank statement import** — Allow users to import transactions directly from CSV or OFX exports provided by their bank, lowering the barrier to entry for users migrating from spreadsheets or other tools.
- [ ] **Data export** — Export filtered transactions and summary reports to CSV or JSON for external analysis, backup, or migration.
- [ ] **Spending trend visualisation** — Add in-TUI sparklines and trend indicators (using Rich's built-in rendering) to show month-over-month changes directly in the pivot tables without requiring a full GUI.

---

## Contributing

Contributions are welcome! Here is how to get started:

1. **Fork** the repository and create your branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Make your changes** and ensure all tests pass:
   ```bash
   pytest
   ```
3. **Commit** your changes with a clear, descriptive message.
4. **Open a Pull Request** against `main`, describing what you changed and why.

Please follow the existing code style and add tests for any new functionality.

---

## License

This project is licensed under the **GNU General Public License v3.0 or later**.
See the [`LICENSE.txt`](LICENSE.txt) file for the full licence text.

---
