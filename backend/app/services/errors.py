class DomainError(Exception):
    """Business rule violation raised by services; API layers map these to HTTP responses."""
    status_code = 400


class NotFound(DomainError):
    status_code = 404


class Forbidden(DomainError):
    status_code = 403


class Conflict(DomainError):
    status_code = 409


class ValidationFailed(DomainError):
    status_code = 422
