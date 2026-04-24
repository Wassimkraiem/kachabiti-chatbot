class ChatbotError(Exception):
    """Base application error."""


class NotFoundError(ChatbotError):
    """Raised when a requested resource does not exist."""


class UnsupportedFileTypeError(ChatbotError):
    """Raised when an uploaded file type is not supported."""


class ConfigurationError(ChatbotError):
    """Raised when required runtime configuration is missing."""


class DocumentProcessingError(ChatbotError):
    """Raised when ingestion or chunking fails."""


class DependencyUnavailableError(ChatbotError):
    """Raised when an external dependency is unavailable."""

