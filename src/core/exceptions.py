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


# --- Finance/API Errors ---


class ApiError(Exception):
    """Base class for external API interaction errors."""

    pass


class ExchangeRateApiError(ApiError):
    """Raised when fetching exchange rates from an external API fails."""

    pass
