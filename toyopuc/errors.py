class ToyopucError(Exception):
    """Base error for TOYOPUC communication."""


class ToyopucProtocolError(ToyopucError):
    """Raised when the response frame is invalid or unexpected."""


class ToyopucTimeoutError(ToyopucProtocolError):
    """Raised on socket timeouts."""


class ToyopucOperationOutcomeUnknownError(ToyopucError):
    """Raised when a state-changing request may have reached the PLC."""
