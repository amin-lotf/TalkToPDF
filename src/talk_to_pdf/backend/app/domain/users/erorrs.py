class RegistrationError(Exception):
    pass


class InvalidCredentialsError(Exception):
    """Raised when email/password combination is invalid."""
    pass


class InactiveUserError(Exception):
    """Raised when a user exists but is not active."""
    pass


class UserNotFoundError(Exception):
    pass