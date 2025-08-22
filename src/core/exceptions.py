# TODO: Use a base class for the entire application instead of normal Exception
# (e.g. inside RepositoryError)


# --- Repository Errors ---


class RepositoryError(Exception):
    """Base class for repository-related errors."""

    pass


class EntityNotFoundError(RepositoryError):
    """Raised when a specific database entity is not found when it was expected to exist."""

    def __init__(self, entity_name: str, parameter: int | float | bool | str):
        super().__init__(f"{entity_name} with parameter {parameter} not found.")


class DuplicateEntityError(RepositoryError):
    """Raised when attempting to create an entity that already violates a UNIQUE constraint."""

    pass
    # def __init__(self, entity_name: str, conflicting_field: str, conflicting_value):
    #     super().__init__(
    #         f"Cannot create {entity_name}. "
    #         f"An entity with {conflicting_field} '{conflicting_value}' already exists."
    #     )


class InvalidParameterError(RepositoryError):
    """Raised when the parameters supplied to a repository method are invalid or
    inconsistent."""

    pass


class ForeignKeyError(RepositoryError):
    """Raised when an operation fails due to a foreign key constraint."""

    pass


# --- Service Layer Errors ---


class ServiceError(Exception):
    """Base class for business logic errors."""

    pass


class OperationNotPermittedError(ServiceError):
    """Raised when a user is not permitted to perform an action (e.g., deleting a primary
    category with children)."""

    pass


class UsernameAlreadyPresentError(ServiceError):
    """Raised when trying to add a new user with an username already present in the
    database."""

    pass


class ServiceUserNotFoundError(ServiceError):
    """Raised when the provided id_user is not present in the database."""

    pass


class ServiceCategoryNotFoundError(ServiceError):
    """Raised when the category of a transaction that need to be added is not present
    in the database."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.details = details or {}


class InvalidCategoryError(ServiceError):
    """Raised when an invalid category is passed to a service.
    E.g. when the category is an income but has a not null secondary."""

    pass


class ServiceDuplicateCategoryError(ServiceError):
    """Raised when trying to add an already existing category to the database."""

    pass


class ServiceTransactionNotFoundError(ServiceError):
    """Raised when a Transaction is not found in the database. Used, for example,
    when editing or deleting a transaction with the given id."""


class ServiceExchangeRateNotFoundError(ServiceError):
    """Raised when an exchange rate is not found in the database. Used, for example,
    when converting some transction into a different currency (e.g. in get_summary)."""

    pass


class ServiceSettingNotFoundError(ServiceError):
    """Raised when a setting with the given name is not found in the database."""

    pass


class ServiceDuplicateCurrencyError(ServiceError):
    """Raised when trying to insert currencies that are already present in the
    database for the given user."""

    pass


class CurrencyNotFoundError(ServiceError):
    """Raise when the required currency (for that user) is not present in the
    database (e.g. when removing a currency)."""

    pass


# --- API Errors ---


class AppException(Exception):
    """Base class for all the API errors"""

    def __init__(self, status_code: int, message: str, code: str):
        self.status_code = status_code
        self.message = message
        self.code = code
        super().__init__(message)


# --- 4xx Errors ---


class BadRequestException(AppException):
    def __init__(self, message: str = "Bad Request"):
        super().__init__(400, message, "BAD_REQUEST")


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(401, message, "UNAUTHORIZED")


class ForbiddenException(AppException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(403, message, "FORBIDDEN")


class NotFoundException(AppException):
    def __init__(self, message: str, code: str):
        super().__init__(404, message, code)


class UserNotFoundException(NotFoundException):
    def __init__(self):
        super().__init__("User not found", "USER_NOT_FOUND")


class CategoryNotFoundException(NotFoundException):
    def __init__(self):
        super().__init__("Category not found", "CATEGORY_NOT_FOUND")


class TransactionNotFoundException(NotFoundException):
    def __init__(self):
        super().__init__("Transaction not found", "TRANSACTION_NOT_FOUND")


class ExchangeRateNotFoundException(NotFoundException):
    def __init__(self):
        super().__init__("Exchange rate not found", "EXCHANGE_RATE_NOT_FOUND")


class SettingNotFoundException(NotFoundException):
    def __init__(self):
        super().__init__("Setting not found", "SETTING_NOT_FOUND")


class ConflictException(AppException):
    def __init__(self, message: str, code: str):
        super().__init__(409, message, code)


class DuplicateUserException(ConflictException):
    def __init__(self):
        super().__init__("User with this username already exists", "DUPLICATE_USER")


class DuplicateCategoryException(ConflictException):
    def __init__(self):
        super().__init__("Category with this name already exists", "DUPLICATE_CATEGORY")


class DuplicateCurrencyException(ConflictException):
    def __init__(self):
        super().__init__("Currency with this code already exists", "DUPLICATE_CURRENCY")


# --- 5xx Errors ---


class InternalServerErrorException(AppException):
    def __init__(self, message: str = "Internal Server Error"):
        super().__init__(500, message, "INTERNAL_SERVER_ERROR")


# --- Finance/API Errors ---


class ApiError(Exception):
    """Base class for external API interaction errors."""

    pass


class ExchangeRateApiError(ApiError):
    """Raised when fetching exchange rates from an external API fails."""

    pass
