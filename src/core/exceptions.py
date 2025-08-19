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


class UserNotFoundError(ServiceError):
    """Raised when the provided id_user is not present in the database."""

    pass


class CategoryNotFoundError(ServiceError):
    """Raised when the category of a transaction that need to be added is not present
    in the database."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.details = details or {}


class InvalidCategoryError(ServiceError):
    """Raised when an invalid category is passed to a service.
    E.g. when the category is an income but has a not null secondary."""

    pass


class DuplicateCategoryError(ServiceError):
    """Raised when trying to add an already existing category to the database."""

    pass


class TransactionNotFoundError(ServiceError):
    """Raised when a Transaction is not found in the database. Used, for example,
    when editing or deleting a transaction with the given id."""


class ExchangeRateNotFoundError(ServiceError):
    """Raised when an exchange rate is not found in the database. Used, for example,
    when converting some transction into a different currency (e.g. in get_summary)."""

    pass


# --- Finance/API Errors ---


class ApiError(Exception):
    """Base class for external API interaction errors."""

    pass


class ExchangeRateApiError(ApiError):
    """Raised when fetching exchange rates from an external API fails."""

    pass
