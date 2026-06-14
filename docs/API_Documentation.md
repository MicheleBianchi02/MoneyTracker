# MoneyTracker API Documentation

## Introduction

Welcome to the MoneyTracker API documentation. This API provides a comprehensive set of endpoints to manage personal finances, including user accounts, transactions, categories, and settings. It's built with FastAPI and uses SQLite for data storage.

Key features include:

- **User Management**: Create, retrieve, update, and delete users.
- **Transaction Tracking**: Log income and expenses with details like category, date, value, and currency.
- **Categorization**: Define custom, year-specific categories for income and expenses, including subcategories.
- **Multi-Currency Support**: Transactions can be recorded in different currencies, and reports can be generated in a preferred currency using exchange rates from the European Central Bank (ECB).
- **Reporting**: Generate summaries and balance reports with various filtering options.

## Authentication

The MoneyTracker API uses **OAuth2 with Bearer Tokens** for authentication. All requests that access user-specific data must include an `Authorization` header with a valid access token.

### Obtaining an Access Token

To obtain an access token, you need to send a `POST` request to the `/token` endpoint with the user's credentials in the request body.

- **Endpoint**: `POST /token`
- **Content-Type**: `application/x-www-form-urlencoded`

**Request Body:**

| Parameter  | Type  | Description          |
| :--------- | :---- | :------------------- |
| `username` | `str` | The user's username. |
| `password` | `str` | The user's password. |

**Example Request:**

```bash
curl -X POST "http://127.0.0.1:8000/token" \
-H "Content-Type: application/x-www-form-urlencoded" \
-d "grant_type=&username=your_username&password=your_password&scope=&client_id=&client_secret="
```

**Successful Response (200 OK):**

The server will respond with a JSON object containing the access token and token type.

```json
{
  "access_token": "your_access_token",
  "token_type": "bearer"
}
```

### Making Authenticated Requests

Once you have an access token, you must include it in the `Authorization` header of your requests for protected endpoints.

**Example:**

```bash
curl -X GET "http://127.0.0.1:8000/users/" \
-H "Authorization: Bearer your_access_token"
```

## Domain Models

### User

| Field      | Type  | Description                         |
| :--------- | :---- | :---------------------------------- |
| `id`       | `int` | The unique identifier for the user. |
| `username` | `str` | The user's username.                |
| `password` | `str` | The user's hashed password.         |

### Category

| Field           | Type                           | Description                                                                                                   |
| :-------------- | :----------------------------- | :------------------------------------------------------------------------------------------------------------ |
| `id_primary`    | `int`                          | The ID of the primary category.                                                                               |
| `id_secondary`  | `int` \| `None`                | The ID of the secondary category (if it's a subcategory).                                                     |
| `id_user`       | `int`                          | The ID of the user who owns the category.                                                                     |
| `year`          | `int`                          | The year the category is valid for.                                                                           |
| `category_type` | `Literal["income", "expense"]` | The type of category.                                                                                         |
| `primary`       | `str`                          | The name of the primary category.                                                                             |
| `secondary`     | `str` \| `None`                | The name of the secondary category. **Note: Subcategories are only supported for 'expense' type categories.** |

### Transaction

| Field         | Type                           | Description                                    |
| :------------ | :----------------------------- | :--------------------------------------------- |
| `id`          | `int`                          | The unique identifier for the transaction.     |
| `id_user`     | `int`                          | The ID of the user who owns the transaction.   |
| `primary`     | `str`                          | The primary category of the transaction.       |
| `secondary`   | `str` \| `None`                | The secondary category of the transaction.     |
| `tr_type`     | `Literal["income", "expense"]` | The type of transaction.                       |
| `tr_date`     | `date`                         | The date of the transaction.                   |
| `name`        | `str`                          | A name for the transaction.                    |
| `value`       | `float`                        | The value of the transaction.                  |
| `currency`    | `str`                          | The currency of the transaction (e.g., "USD"). |
| `description` | `str`                          | A description for the transaction.             |

### Currency

| Field              | Type             | Description                                   |
| :----------------- | :--------------- | :-------------------------------------------- |
| `code`             | `str`            | The currency code (e.g., "USD").              |
| `symbol`           | `str`            | The currency symbol (e.g., "$").              |
| `name`             | `str`            | The name of the currency (e.g., "US Dollar"). |
| `is_active`        | `bool`           | Whether the currency is active.               |
| `deprecation_date` | `date` \| `None` | The date the currency was deprecated.         |

### Setting

| Field              | Type                                | Description                                 |
| :----------------- | :---------------------------------- | :------------------------------------------ |
| `id_setting`       | `int`                               | The unique identifier for the setting.      |
| `name`             | `str`                               | The name of the setting.                    |
| `constrained`      | `bool`                              | Whether the setting has constrained values. |
| `allowed_settings` | `list[dict[str, str]]`              | A list of allowed values for the setting.   |
| `value`            | `str` \| `bool` \| `int` \| `float` | The value of the setting.                   |

#### Standard Settings Keys

The following are standard values for the `name` field that the frontend should expect:

| Setting Name       | Description                                  | Example Value    |
| :----------------- | :------------------------------------------- | :--------------- |
| `default_currency` | The user's preferred currency for reporting. | `"EUR"`, `"USD"` |
| `language`         | The user's preferred interface language.     | `"en"`, `"it"`   |

## Response Models

This section defines the structure of specific response objects returned by the API, particularly from the Transactions endpoints.

### TransactionResponse

| Field          | Type                   | Description                                                                                                        |
| :------------- | :--------------------- | :----------------------------------------------------------------------------------------------------------------- |
| `transactions` | `list[TransactionOut]` | A list of transaction objects.                                                                                     |
| `is_valid`     | `bool`                 | Indicates if the currency conversion was successful for all transactions (`true` if successful or not applicable). |

### SummaryResponse

| Field      | Type                                     | Description                                                                                                                                                                                                             |
| :--------- | :--------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `summary`  | `dict[str, dict[str, dict[str, float]]]` | A nested dictionary containing the transaction summary. The structure is `{ "primary_category": { "secondary_category": { "YYYY-MM": total_value } } }`. Example: `{"Groceries": {"Supermarket": {"2024-01": 250.75}}}` |
| `is_valid` | `bool`                                   | Indicates if the currency conversion was successful for all summarized transactions (`true` if successful).                                                                                                             |

### BalanceResponse

| Field         | Type    | Description                                                                                                              |
| :------------ | :------ | :----------------------------------------------------------------------------------------------------------------------- |
| `tot_expense` | `float` | The total value of all expense transactions for the given period.                                                        |
| `tot_income`  | `float` | The total value of all income transactions for the given period.                                                         |
| `is_valid`    | `bool`  | Indicates if the currency conversion was successful for all transactions included in the balance (`true` if successful). |

## API Endpoints

### Users

Endpoints for managing user accounts.

---

#### Create User

- **Endpoint**: `POST /users/`
- **Description**: Creates a new user account.
- **Request Body**: `UserIn`
  ```json
  {
    "username": "newuser",
    "password": "newpassword"
  }
  ```
- **Successful Response (201)**:
  ```json
  {
    "message": "User created successfully",
    "id_user": 1,
    "access_token": "your_access_token",
    "token_type": "bearer"
  }
  ```
- **Error Responses**:
  - `409 Conflict`: If the username already exists.
  - `500 Internal Server Error`: For other server-side errors.

---

#### Get Users

- **Endpoint**: `GET /users/`
- **Description**: Retrieves a list of users. Can be filtered by username.
- **Authentication**: Required.
- **Query Parameters**:
  - `username` (optional, string): Filter users by username.
- **Successful Response (200 OK)**: A list of `UserOut` objects.
  ```json
  [
    {
      "id": 1,
      "username": "testuser",
      "password": "hashed_password"
    }
  ]
  ```
- **Error Responses**:
  - `500 Internal Server Error`: For server-side errors.

---

#### Edit User

- **Endpoint**: `PUT /users/`
- **Description**: Edits the current authenticated user's information (username or password).
- **Authentication**: Required.
- **Request Body**: `UserEdit`
  ```json
  {
    "new_username": "updateduser",
    "new_password": "new_password",
    "old_password": "current_password"
  }
  ```
- **Successful Response (204 No Content)**
- **Error Responses**:
  - `401 Unauthorized`: If the old password is incorrect.
  - `404 Not Found`: If the user is not found.
  - `409 Conflict`: If the new username is already taken.
  - `500 Internal Server Error`: For other server-side errors.

---

#### Delete User

- **Endpoint**: `DELETE /users/`
- **Description**: Deletes the current authenticated user's account.
- **Authentication**: Required.
- **Request Body**: `UserDeleteConfirmation`
  ```json
  {
    "current_password": "current_password"
  }
  ```
- **Successful Response (204 No Content)**
- **Error Responses**:
  - `401 Unauthorized`: If the password is incorrect.
  - `404 Not Found`: If the user is not found.
  - `500 Internal Server Error`: For other server-side errors.

### Transactions

Endpoints for managing financial transactions. All endpoints require authentication.

---

#### Add Transaction(s)

- **Endpoint**: `POST /transactions/`
- **Description**: Adds one or more new transactions.
- **Request Body**: A single `TransactionIn` object or a list of `TransactionIn` objects.
  ```json
  {
    "primary": "Groceries",
    "secondary": "Supermarket",
    "tr_type": "expense",
    "tr_date": "2024-01-15",
    "name": "Weekly shopping",
    "value": 75.5,
    "currency": "USD",
    "description": "Groceries for the week"
  }
  ```
- **Successful Response (201 Created)**:
  ```json
  {
    "message": "Transaction created successfully."
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: If the currency is invalid.
  - `404 Not Found`: If the user or category is not found.
  - `500 Internal Server Error`: For other server-side errors.

---

#### Get Transactions

- **Endpoint**: `GET /transactions/`
- **Description**: Retrieves a list of transactions with extensive filtering options.
- **Query Parameters**:
  - `begin_date` (optional, date): Start date for filtering.
  - `end_date` (optional, date): End date for filtering.
  - `to_currency` (optional, string): The currency to convert the transaction values to.
  - `tr_type` (optional, `Literal["income", "expense"]`): Filter by transaction type.
  - `primary` (optional, string): Filter by primary category.
  - `secondary` (optional, string): Filter by secondary category.
  - `order` (optional, `Literal["name", "date", "value", "currency", "primary", "secondary"]`): Field to order by.
  - `order_dir` (optional, `Literal["ASC", "DESC"]`): Order direction. Default `ASC`.
  - `limit` (optional, int): Limit the number of results.
  - `offset` (optional, int): Offset for pagination.
  - `name` (optional, string): Filter by transaction name.
- **Successful Response (200 OK)**: `TransactionResponse`
  ```json
  {
    "transactions": [
      {
        "id": 1,
        "id_user": 1,
        "primary": "Groceries",
        "secondary": "Supermarket",
        "tr_type": "expense",
        "tr_date": "2024-01-15",
        "name": "Weekly shopping",
        "value": 75.5,
        "currency": "USD",
        "description": "Groceries for the week"
      }
    ],
    "is_valid": true
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: If filtering parameters are invalid.
  - `500 Internal Server Error`: For server-side errors.

---

#### Get Transaction Summary

- **Endpoint**: `GET /transactions/summary/`
- **Description**: Retrieves a summary of transactions grouped by category.
- **Query Parameters**:
  - `to_currency` (required, string): The currency for the summary.
  - `tr_type` (required, `Literal["income", "expense"]`): The transaction type.
  - `begin_date` (optional, date): Start date.
  - `end_date` (optional, date): End date.
  - `primary` (optional, string): Filter by primary category.
  - `secondary` (optional, string): Filter by secondary category.
- **Successful Response (200 OK)**: `SummaryResponse`
- **Error Responses**:
  - `400 Bad Request`: If the currency is invalid.
  - `500 Internal Server Error`: For server-side errors.

---

#### Get Balance

- **Endpoint**: `GET /transactions/balance/`
- **Description**: Calculates total income and expenses.
- **Query Parameters**:
  - `to_currency` (required, string): The currency for the balance calculation.
  - `begin_date` (optional, date): Start date.
  - `end_date` (optional, date): End date.
  - `tr_type` (optional, `Literal["income", "expense"]`): Filter by transaction type.
  - `primary` (optional, string): Filter by primary category.
  - `secondary` (optional, string): Filter by secondary category.
- **Successful Response (200 OK)**: `BalanceResponse`
  ```json
  {
    "tot_expense": 150.75,
    "tot_income": 2000.0,
    "is_valid": true
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: If the currency is invalid.
  - `500 Internal Server Error`: For server-side errors.

---

#### Edit Transaction

- **Endpoint**: `PUT /transactions/{id_tr}`
- **Description**: Edits an existing transaction.
- **Path Parameters**:
  - `id_tr` (int): The ID of the transaction to edit.
- **Request Body**: `TransactionIn`
- **Successful Response (204 No Content)**
- **Error Responses**:
  - `400 Bad Request`: If the currency is invalid.
  - `403 Forbidden`: If the user does not have permission to edit the transaction.
  - `404 Not Found`: If the transaction or category is not found.
  - `500 Internal Server Error`: For other server-side errors.

---

#### Delete Transaction

- **Endpoint**: `DELETE /transactions/{id_tr}`
- **Description**: Deletes a transaction.
- **Path Parameters**:
  - `id_tr` (int): The ID of the transaction to delete.
- **Successful Response (204 No Content)**
- **Error Responses**:
  - `403 Forbidden`: If the user does not have permission to delete the transaction.
  - `404 Not Found`: If the transaction is not found.
  - `500 Internal Server Error`: For other server-side errors.

### Categories

Endpoints for managing categories and subcategories. All endpoints require authentication.

---

#### Add Category

- **Endpoint**: `POST /categories/`
- **Description**: Adds one or more new categories.
- **Request Body**: A list of `CategoryIn` objects.
  ```json
  [
    {
      "year": 2024,
      "category_type": "expense",
      "primary": "Utilities",
      "secondary": "Internet"
    }
  ]
  ```
- **Successful Response (201 Created)**:
  ```json
  {
    "message": "Category added successfully."
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: If the category data is invalid.
  - `404 Not Found`: If the user is not found.
  - `409 Conflict`: If the category already exists.
  - `500 Internal Server Error`: For other server-side errors.

---

#### Get Primary Categories

- **Endpoint**: `GET /categories/primary/`
- **Description**: Retrieves a list of primary categories.
- **Query Parameters**:
  - `year` (optional, int): Filter by year.
  - `cat_type` (optional, `Literal["income", "expense"]`): Filter by category type.
- **Successful Response (200 OK)**: A list of `CategoryOut` objects.
- **Error Responses**:
  - `500 Internal Server Error`: For server-side errors.

---

#### Get Secondary Categories

- **Endpoint**: `GET /categories/secondary/`
- **Description**: Retrieves a list of secondary categories.
- **Query Parameters**:
  - `year` (optional, int): Filter by year.
  - `primary` (optional, string): Filter by primary category name.
- **Successful Response (200 OK)**: A list of `CategoryOut` objects.
- **Error Responses**:
  - `500 Internal Server Error`: For server-side errors.

---

#### Get All Categories

- **Endpoint**: `GET /categories/`
- **Description**: Retrieves all categories for the user.
- **Query Parameters**:
  - `year` (optional, int): Filter by year.
  - `cat_type` (optional, `Literal["income", "expense"]`): Filter by category type.
- **Successful Response (200 OK)**: A list of `CategoryOut` objects.
- **Error Responses**:
  - `500 Internal Server Error`: For server-side errors.

---

#### Edit Category

- **Endpoint**: `PUT /categories/{id_cat}`
- **Description**: Edits the name of a category.
- **Path Parameters**:
  - `id_cat` (int): The ID of the category to edit.
- **Query Parameters**:
  - `new_name` (required, string): The new name for the category.
- **Successful Response (204 No Content)**
- **Error Responses**:
  - `403 Forbidden`: If the user does not have permission to edit the category.
  - `404 Not Found`: If the category is not found.
  - `500 Internal Server Error`: For other server-side errors.

---

#### Delete Category

- **Endpoint**: `DELETE /categories/{id_cat}`
- **Description**: Deletes a category. It will fail if the category is in use by transactions or if it's a primary category with subcategories.
- **Path Parameters**:
  - `id_cat` (int): The ID of the category to delete.
- **Successful Response (204 No Content)**
- **Error Responses**:
  - `403 Forbidden`: If the user does not have permission to delete the category.
  - `404 Not Found`: If the category is not found.
  - `409 Conflict`: If the category is in use.
  - `500 Internal Server Error`: For other server-side errors.

### Settings

Endpoints for managing user and application settings, including currencies.

---

#### Add or Update User Setting

- **Endpoint**: `POST /settings/`
- **Description**: Adds or updates a user-specific setting.
  - **Constrained Settings** (e.g., `language`, `value_format`): The `value` **must** be one of the `item_value` strings found in the `allowed_settings` list returned by the `GET /settings/` endpoint.
  - **Unconstrained Settings** (e.g., `default_currency`): The `value` can be any valid string (e.g., a currency code).
- **Authentication**: Required.
- **Request Body**:
  ```json
  {
    "setting_name": "language",
    "value": "it"
  }
  ```
- **Successful Response (204 No Content)**
- **Error Responses**:
  - `400 Bad Request`: If the value is not allowed for a constrained setting.
  - `404 Not Found`: If the setting name is not valid.
  - `500 Internal Server Error`: For server-side errors.

---

#### Get Default Settings

- **Endpoint**: `GET /settings/default/`
- **Description**: Retrieves the default application settings.
- **Query Parameters**:
  - `setting_name` (optional, string): Filter by setting name.
- **Successful Response (200 OK)**: A list of `Setting` objects.
- **Error Responses**:
  - `500 Internal Server Error`: For server-side errors.

---

#### Get User Settings

- **Endpoint**: `GET /settings/`
- **Description**: Retrieves user-specific settings. **To retrieve the user's preferences, filter by the specific `setting_name`**.
  - To get the **default currency**: `GET /settings/?setting_name=default_currency`
  - To get the **language**: `GET /settings/?setting_name=language`
- **Authentication**: Required.
- **Query Parameters**:
  - `setting_name` (optional, string): Filter by setting name (e.g., `default_currency`, `language`).
- **Successful Response (200 OK)**: A list of `Setting` objects.
- **Error Responses**:
  - `500 Internal Server Error`: For server-side errors.

---

#### Add User Currency

- **Endpoint**: `POST /settings/currencies/`
- **Description**: Adds a currency for the user to use.
- **Authentication**: Required.
- **Request Body**: `string` (The currency code, e.g., `"CAD"`)
- **Successful Response (204 No Content)**
- **Error Responses**:
  - `400 Bad Request`: If the currency code is invalid.
  - `409 Conflict`: If the currency has already been added.
  - `500 Internal Server Error`: For server-side errors.

---

#### Get Available Currencies

- **Endpoint**: `GET /settings/currencies/available/`
- **Description**: Retrieves all available currencies in the system.
- **Query Parameters**:
  - `is_active` (optional, bool): Filter for active currencies.
- **Successful Response (200 OK)**: A list of `Currency` objects.
- **Error Responses**:
  - `500 Internal Server Error`: For server-side errors.

---

#### Get User Currencies

- **Endpoint**: `GET /settings/currencies/`
- **Description**: Retrieves all currencies for the authenticated user.
- **Authentication**: Required.
- **Query Parameters**:
  - `is_active` (optional, bool): Filter for active currencies.
- **Successful Response (200 OK)**: A list of `Currency` objects.
- **Error Responses**:
  - `500 Internal Server Error`: For server-side errors.

---

#### Delete User Currency

- **Endpoint**: `DELETE /settings/currencies/`
- **Description**: Deletes a currency for the user.
- **Authentication**: Required.
- **Query Parameters**:
  - `currency_code` (required, string): The code of the currency to delete (e.g., "CAD").
- **Successful Response (204 No Content)**
- **Error Responses**:
  - `400 Bad Request`: If the currency is not found for the user.
  - `500 Internal Server Error`: For server-side errors.
