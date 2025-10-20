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

Multi-currency is allowed by the ECB (European Central Banck) API.
In the service relative to the exchange rates it is present a list of all the available
currencies with relative code, symbol, name, deprecation_date (if present). Of course,
the active or withdrawn currencies are defined when the app is compiled. Then, if a new
currency is deprecated, other methods need to be used to handle them (see below).

It follow a schema of how the exchange rates are handled:

1. The first time the app is run (after installation) there can be two cases:

   - **Connection is present**. A request to the rates provider is done using only the
     active currencies present in the list defined above. The date range is from the
     first available date (2001-01-01) until the startup date. With the returned values
     the app first check if some currency are deprecated. For the new identified
     withdrawn currencies, a deprecation date is estimated. Using these information
     and also the one present in the list defined above, all currencies are saved in
     the currencies table of the database (the deprecation date and wheter it is active
     or not is also saved in the same table). The startup date is saved in the app_config
     table under the key `deprecation_check_date` (variable called
     `DEPRECATION_CHECK_DATE_CONFIG_NAME`). Then, with the same returned data, the
     exchange rate present in the database from an arbitrary date (at the moment it is
     the first day of the startup year) until the startup date are saved in the database
     (only for the active currencies in that period). For currencies deprecated within
     that period, exchange rate from the starting date until the deprecation date will
     be saved. At the end, that starting date is saved inside the app_config table of
     the database under the key: `continuous_exchange_rate_start_date` (variable
     called `EXC_DATE_CONFIG_NAME`).

   - **Offline**. In this case the API request will fail. Since no information is
     known on the currency state, the list defined above is used. Even if there would
     be any withdrawn currency, the currency list is saved in the currencies table of the
     database. The difference is that the startup date is not saved inside the app_config
     table of the database under the key `deprecation_check_date` (see later for the reason).
     Then, a starting date is still defined (as above) and the exchange rate for all
     active currencies are saved in the db with a value of 1 (or an estimation of that
     value if present in the list defined before). All those rates will have the
     `is_updated` parameter set to False. As before, the starting date is saved in
     app_config table under the key `continuous_exchange_rate_start_date`.

2. For all other startup different functions are called.

   - First the value of `deprecation_check_date` is taken from the database. If
     nothing is found or the date is too old (30 or more days in the past) the
     deprecation check is done again. If the connection is not present, nothing is done.
     In the other case there can be two outcome. If no withdrawn currencies are found,
     nothing is done. Otherwise a conflict check is performed (see below). Only if the
     connection is present, the `deprecation_check_date` is updated to the current date.
     At the end, the currencies table in the database is updated.

   - Second, new rates are added. First we take the last exchange rate in the database
     (closest to the current date). If not present the value of `continuous_exchange_rate_start_date`
     is taken (if missing is then defined), and all exchange rates from that date until
     today are added. If the connection is not present a value of 1 is assigned (this
     should not happen considering point 1, but it is just a safety mechanism). If some
     rate are found, the latest date is taken, and if it's smaller than yesterday, the
     new rates are added (given by the API provider). If the connection is not present,
     nothing is added.
   - Third, old rates are updated. All rates that have the `is_updated` parameter set
     to False are taken from the database. Relative dates and currencies are selected
     and fetched from the API. The rates for the returned data are updated.

   This cycle repeat at every startup or evry 10 hours (saved in the parameter
   `EXC_ADD_INTERVAL_SECONDS`) such that if the server remain on for long period, the
   rates are still added/updated correctly. This is performed on a separate thread and
   asyncronously with respect to the UI.

3. The user is not allowed to add transactions with deprecated currencies (i.e.
   transaction's date bigger than the withdrawn date for that currency). There can be
   some edge cases though. Say a user uses the app mainly offline. Then, after a certain
   period he open the app with internet connection and find out that a currency has been
   withdrawn (theoretically in the real world he should know that since that currency
   is not available in the real world, but these cases should be taken into consideration).
   He will have some transactions with a deprecated currency, and this is not allowed.
   So, after the deprecation_check function of point 2 identify a newly deprecated
   currency, it run the conflict_check function. This function scan the entire
   database for transactions that uses that currency and with date bigger than the
   estimated withdrawn date and, if found, it saves those transactions in the
   `data_conflicts` table of the database. If no transactions are found the exchange
   rates saved for that currency are deleted. Then, a dedicated service will handle
   those conflicts (for instance it can ask for the user to edit or delete those
   transaction, and then delete the rates with date bigger than the withdrawn date).
   Those cases can happen when a transaction is added older than
   `continuous_exchange_rate_start_date` but without knowing that that currency was
   already deprecated (since there was not internet connection and the rates must
   be added in any case).

4. Transaction older than `continuous_exchange_rate_start_date`. For old transactions,
   exchange rates in a period around that date (can be the month or just the
   transaction's date) are added to the database. If the connection is not present
   the rate value used is either 1 or the value of the closest rate (in order to still
   give reasonable rate even if the real one is not known). In this case the `is_updated`
   parameter is False. These rates will be updated by the function defined at point 2.
   This process is done also if the transaction date is modified.

   For transaction above that date, nothing is done.

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
