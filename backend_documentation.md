# MoneyTracker Backend Documentation

This document provides an overview of the backend architecture, key features, and operational rules for the MoneyTracker application.

## 1. Core Architecture

The backend is built on a clean, decoupled architecture designed for maintainability and data integrity.

### Unit of Work Pattern (`UnitOfWork`)

- **Purpose**: To ensure data consistency, all database operations are wrapped in a "Unit of Work". This guarantees that a series of related actions (e.g., adding a transaction and updating a balance) either all succeed (`commit`) or all fail (`rollback`).
- **Usage**: All interactions with the database **must** go through the `UnitOfWork`. It provides access to the repositories for each data entity.

  ```python
  from src.infrastructure.sqlite.unit_of_work import UnitOfWork

  with UnitOfWork(db_path) as uow:
      uow.user.add(...)
      uow.transaction.get(...)
      # The transaction is automatically committed on successful exit.
  ```

### Repository Pattern

- **Purpose**: Each core data entity (User, Category, Transaction, etc.) has its own repository class (e.g., `TransactionRepository`). This pattern isolates the data access logic from the business logic.
- **Benefit**: If you were to switch from SQLite to another database, you would only need to rewrite the repositories, not the application's business logic.

### Database

- **Technology**: The backend uses **SQLite 3**.
- **Concurrency**: It runs in **Write-Ahead Logging (WAL)** mode, which allows for high concurrency (i.e., reading and writing can happen at the same time without blocking).
- **Data Integrity**:
  - **Foreign Keys**: Enforced at the database level (`PRAGMA foreign_keys = ON`).
  - **Strict Typing**: Tables are created with the `STRICT` keyword, preventing data type mismatches (e.g., storing text in an integer column).

## 2. Key Features & Concepts

### Hierarchical Categories

- Categories can be either **Primary** (e.g., "Transport") or **Secondary** (e.g., "Gas", which belongs to "Transport").
- They are specific to a **user**, a **year**, and a **type** (`'expense'` or `'income'`).
- **Rule**: `income` categories cannot have secondary categories.

### Multi-Currency Transactions

- Transactions can be recorded in any currency (e.g., 'USD', 'EUR', 'JPY').
- The system stores daily exchange rates to a base currency.

### Dynamic Financial Summaries

- The `transaction.get_summary()` method is a powerful feature that can calculate total income or expenses across different categories and months.
- It automatically converts all transaction values to a single, user-specified target currency, providing a unified financial overview.

### Flexible User Settings

- The backend uses an Entity-Attribute-Value (EAV) model for settings.
- This allows for creating new user-specific settings (e.g., 'theme', 'language') without changing the database schema. Settings can be constrained (a list of allowed values) or unconstrained (free-form).

## 3. Critical Rules & External Dependencies

This section outlines the rules that any client (e.g., a GUI, a web frontend) **must** follow to interact with the backend correctly.

1.  **Category Must Exist Before a Transaction Is Added**:

    - You cannot add a transaction for a category that does not already exist for that specific `user`, `year`, and `type`.
    - **Frontend Responsibility**: Before allowing a user to save a transaction, the frontend must ensure the selected category exists. If it doesn't, it must first call `uow.category.add()` to create it.

2.  **User Deletion is Permanent and Cascading**:

    - When a user is deleted via `uow.user.delete()`, the `ON DELETE CASCADE` rule in the database will **automatically and irreversibly delete all data associated with that user**. This includes all their transactions, categories, and settings.
    - **Frontend Responsibility**: The UI must provide a very clear and strong warning to the user before allowing them to delete their account.

3.  **Exchange Rates Are Required for Summaries**:

    - The `get_summary()` feature relies entirely on the exchange rates present in the `exchange_rates` table for the relevant dates.
    - **External Responsibility**: The application needs a separate process or service to fetch daily exchange rates from an external API and store them in the database using `uow.exchange_rate.add()`. The backend does not do this automatically.

4.  **Critical Category Fields are Immutable**:

    - A category's `id_user`, `category_year`, and `category_type` cannot be edited after creation.
    - To "move" a category to a new year, the frontend must treat it as creating a new category and potentially moving associated transactions.

5.  **Transaction Editing and Year Changes**:
    - When a user edits a transaction and changes its date to a different year, the transaction's `id_category` must be updated to point to a valid category for the **new year**.
    - The backend's `transaction.edit()` method handles the lookup, but the frontend must supply the correct category _names_ for the new year.
