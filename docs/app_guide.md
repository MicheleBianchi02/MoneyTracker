# MoneyTracker Application Guide

## 1. Introduction

This document provides a detailed explanation of the core concepts and functionalities of the MoneyTracker application. It is intended to be used alongside the `API_Documentation.md` to give frontend developers a complete understanding of how the application works from a user's perspective, enabling them to build a client without needing to inspect the backend codebase.

The philosophy behind MoneyTracker is to provide a flexible and realistic way to track personal finances. The two most important concepts that embody this philosophy are the **Annual Category System** and **Multi-Currency Support**.

## 2. Core Concepts

### 2.1. The Annual Category System

One of the most unique features of MoneyTracker is that **categories are year-specific**. This design choice is intentional and based on the idea that a person's financial habits, interests, and spending patterns evolve over time.

**How it Works:**

- When a user defines categories for their income and expenses, each category is tied to a specific year.
- At the beginning of a new year (e.g., January 1st), the categories from the previous year are **not** automatically carried over. The user starts with a clean slate for the new year.
- The user is expected to create a new set of categories for the current year. They can choose to recreate the same categories from the previous year or define entirely new ones.

**Rationale:**

- **Flexibility**: Your interests and spending habits change. You might pick up a new hobby, start a new project, or have a one-off expense that doesn't make sense to keep as a category forever. This system prevents clutter from old, irrelevant categories.
- **Accurate Annual Reporting**: By having year-specific categories, you can get a very clear and accurate picture of your finances for that particular year without interference from previous years' data structures.
- **Encourages Review**: The need to set up categories at the start of a new year encourages a healthy annual financial review process, allowing the user to consciously decide what they want to track in the coming year.

**Frontend Implementation Notes:**

- When a user wants to add a transaction, the frontend should fetch the categories for the `year` of the transaction's date.
- When a user is viewing data from a previous year, the frontend should use that year's specific category list.
- At the start of a new year, the UI could prompt the user to set up their categories for the new year. A helpful feature would be to allow them to "copy" or "import" their categories from the previous year as a starting point, which they can then edit.

**Primary and Secondary Categories:**

- To provide more detailed tracking, the system supports a two-level hierarchy for **expense categories**:
  - **Primary Category**: A broad classification (e.g., "Transportation").
  - **Secondary Category (Subcategory)**: A more specific classification within a primary category (e.g., "Gas", "Public Transit", "Maintenance").
- A primary category can exist on its own, without any secondary categories.
- **Important**: Subcategories are **not** supported for `income` type categories. Income categories only have a primary level.

### 2.2. Multi-Currency Functionality

MoneyTracker is designed for users who deal with multiple currencies, whether through travel, international business, or investments.

**How it Works:**

- **User-Defined Currencies**: Each user can maintain their own list of active currencies through the `/settings/currencies` endpoints. Before a user can log a transaction in a specific currency, they must add it to their personal list of active currencies.
- **Transaction Logging**: When adding a transaction, the user specifies the `currency` and the `value` in that currency.
- **Reporting in a Target Currency**: The real power comes in the reporting endpoints (`/transactions/`, `/transactions/summary/`, `/transactions/balance/`). These endpoints accept a `to_currency` parameter, which tells the system to convert all transaction values into that single target currency for the report.

**Exchange Rates:**

- The system fetches daily exchange rates from the **European Central Bank (ECB)**.
- The conversion is based on the exchange rate on the **date of the transaction**.

**The `is_valid` Flag:**

- In API responses for reports (`TransactionResponse`, `SummaryResponse`, `BalanceResponse`), you will find an `is_valid` boolean flag.
- This flag indicates whether the backend was able to successfully fetch exchange rates for **all** transactions included in the report.
- If `is_valid` is `false`, it means the report may be incomplete or inaccurate because at least one currency conversion failed. This could happen if the ECB did not provide a rate for a specific currency on a specific day.
- **Frontend Implementation Note**: If `is_valid` is `false`, the UI should display a warning to the user indicating that the totals may not be accurate due to missing exchange rate data.

### 2.3. User Accounts and Data Isolation

- MoneyTracker is a multi-user application.
- All data—including transactions, categories, and settings—is strictly scoped to the authenticated user.
- A user can only ever see and manage their own data. This is enforced by the backend using the authentication token provided with each API request.

### 2.4. Global Application Settings

The application stores user preferences in a generic `settings` table. These settings are crucial for the frontend to determine how to render the UI and what defaults to use for reports.

**Key Settings:**

- **`default_currency`**:
  - **Usage**: Used as the default target currency (`to_currency`) for the Dashboard and Balance reports. If the user doesn't manually select a currency filter, the frontend should use this value.
  - **Type**: Unconstrained (Free Text).
  - **How to Set**: The frontend should fetch the list of _User Active Currencies_, let the user select one, and then save that selection as the `default_currency` setting.

- **`language`**:
  - **Usage**: Determines the localization of the frontend interface (e.g., 'en', 'it', 'fr').
  - **Type**: Constrained (Selection List).
  - **How to Set**: The frontend **must** first fetch the setting object for `language` using `GET /settings/?setting_name=language`. This object contains an `allowed_settings` list (e.g., `[{ "item_value": "en", "caption": "English" }, ...]`). The UI should render a dropdown menu using these captions and values. When the user saves, the selected `item_value` is sent back to the API.

**Constrained vs. Unconstrained:**

- **Constrained (`constrained: true`)**: The setting has a fixed set of valid options defined by the backend. The frontend must always validate user input against the `allowed_settings` list provided by the API.
- **Unconstrained (`constrained: false`)**: The setting accepts any string value. However, the frontend often needs to provide its own logic for what is "valid" (e.g., for `default_currency`, the valid values are the user's active currencies, which is a dynamic list not hardcoded in the settings definition).

## 3. Practical Workflows

This section outlines common user scenarios to help a frontend developer design the user experience.

### 3.1. First-Time User Onboarding

Here is a conceptual walkthrough of what a new user would do to get started with MoneyTracker.

1.  **Create an Account**: The user signs up via the `POST /users/` endpoint. The application should immediately log them in by storing the returned access token.
2.  **Activate Currencies**: The user needs to decide which currencies they will be logging transactions in.
    - The UI should call `GET /settings/currencies/available/` to show a list of all possible currencies supported by the system.
    - The user selects the currencies they want to use (e.g., USD, EUR, JPY).
    - For each selected currency, the UI makes a `POST /settings/currencies/` request to add it to the user's active list.
3.  **Define Categories for the Current Year**: The user needs to set up their initial set of categories for tracking income and expenses.
    - The UI should determine the current year.
    - The user creates primary categories (e.g., "Salary", "Groceries", "Rent") and, optionally, secondary categories (e.g., "Groceries" -> "Supermarket", "Farmer's Market").
    - The UI collects this information and sends it to the `POST /categories/` endpoint. The `year` field for each category will be the current year.
4.  **Start Tracking**: The user can now begin adding transactions via the `POST /transactions/` endpoint, selecting from the categories they just created.

### 3.2. Starting a New Year

On January 1st, a user's existing categories are not automatically available for the new year. The frontend should be designed to handle this transition smoothly.

1.  **New Year Detection**: When the user opens the app in a new year, the UI will find that a call to `GET /categories/` with the current year returns an empty list.
2.  **Prompt for Category Setup**: The application should recognize this and prompt the user to set up their categories for the new year.
3.  **Option to Import from Previous Year**: To make this process easier, the UI should offer an "Import from last year" button.
    - If the user clicks this, the frontend will call `GET /categories/` with the _previous_ year's value.
    - It will then take the returned list of categories, change the `year` field on each one to the _current_ year, and send this new list to the `POST /categories/` endpoint.
4.  **Option to Start Fresh**: The user should also have the option to decline the import and create their categories from scratch for the new year.

- **Continue Tracking**: Once categories for the new year are defined, the user can continue logging transactions as usual. All new transactions will be associated with the new year's categories. Reporting for previous years will remain unaffected and will still be mapped to the categories defined for those years.

## 4. Frontend Implementation Insights from the TUI

The existing Text-based User Interface (TUI) provides a valuable reference for how a professional frontend can be designed. It reveals user-friendly workflows and UI patterns that are not explicitly detailed in the API specification alone.

### 4.1. Dashboard View (`dashboard_tab.py`)

- **Default View**: The dashboard defaults to showing transactions for the **current month**.
- **Visual Cues**: Expenses are consistently colored **red** and incomes **green** to provide immediate visual feedback.
- **Balance Display**: The view prominently displays the total income, total expenses, and the final balance for the selected period.
- **Currency Conversion Warnings**: If the `is_valid` flag is `false` in an API response, the TUI displays a warning: "⚠ Some currency conversion rates are not up to date." A professional frontend should do the same to inform the user that the displayed totals may be inaccurate.
- **Confirmation Modals**: Before adding or editing a transaction, the TUI presents a summary of the data and asks for confirmation. This is a good practice to prevent accidental submissions.

### 4.2. Expense and Income Views (`expense_tab.py`, `income_tab.py`)

- **Pivot Table for Summaries**: The expense and income tabs are not simple lists. They are presented as **pivot tables** (or summary tables) where:
  - Rows represent categories (and subcategories for expenses).
  - Columns represent the 12 months of the year.
  - Cell values are the sum of transactions for that category/month.
- **Client-Side Data Aggregation**: The TUI fetches the raw summary data from the API and then performs significant client-side processing to build this pivot table view, filling in months with no transactions with zeros to create a complete and easy-to-read table.
- **Totals**: The tables include row totals (total for each category over the year) and a final column total (total for each month across all categories).
- **Toggle Subcategory Visibility**: The expense view allows the user to show or hide subcategories, enabling them to switch between a high-level overview and a detailed breakdown.

### 4.3. Category Management (`category_tab.py`)

- **Visual Separation**: The TUI uses separate tables for "Income" and "Expense" categories, even when displayed on the same screen, to create a clear distinction.
- **Deletion Warnings**: When a user tries to delete a category, the TUI handles the business logic gracefully. If the API returns an error indicating the category is in use, the TUI displays a user-friendly message, such as "It is not possible to delete a category with existing sub-categories" or "There are X transactions pertaining to this category. Please edit/delete them first."

### 4.4. Settings Management (`setting.py`)

- **Currency Management UI**: The TUI provides a clear interface for currency management:
  - It displays a table of the user's currently active currencies.
  - It separately displays a table of all _other_ available currencies that the user can add.
  - When adding a currency, it checks if the currency is deprecated and warns the user.
  - It prevents the user from deleting their last remaining active currency, ensuring they always have at least one to fall back on. This is a client-side check that a professional frontend should also implement.
