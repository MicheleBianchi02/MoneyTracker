from dataclasses import dataclass


@dataclass
class User:
    username: str
    password: str
    id: int = 1  # set bu the database

    def __eq__(self, other):
        """Ignore the .id parameter when equating two User

        Need this because the .id parameter is noramlly set automatically by the
        database, meaning that is a priori unknown.
        This is needed, for istance during testing.
        """

        if not isinstance(other, User):
            raise NotImplementedError(
                f"Equivalence between User and {type(other)} is not supported",
            )

        return (
            self.username,
            self.password,
        ) == (
            other.username,
            other.password,
        )
