from __future__ import annotations

from enum import Enum


class ToyopucError(Exception):
    """Base error for TOYOPUC communication."""


class ToyopucProtocolError(ToyopucError):
    """Raised when the response frame is invalid or unexpected."""


class ToyopucTimeoutError(ToyopucError):
    """Raised when the configured connect or transaction deadline expires."""


class ToyopucCancelledError(ToyopucError):
    """Raised when an operation is cancelled before its outcome becomes uncertain."""


class ToyopucTransportError(ToyopucError):
    """Raised for transport failures distinct from timeout and protocol decoding."""


class ToyopucNotConnectedError(ToyopucError):
    """Raised when an explicit reconnect is required before another command."""


class ToyopucClosedError(ToyopucError):
    """Raised when close retires the operation's transport generation."""


class ToyopucPlcError(ToyopucError):
    """Raised for a syntactically valid PLC NG response."""


class ToyopucOutcomeUnknownReason(str, Enum):
    """Machine-readable reason for an unknown state-changing operation outcome."""

    TIMEOUT = "timeout"
    CANCELLATION = "cancellation"
    CLOSED = "closed"
    TRANSPORT = "transport"
    MALFORMED_RESPONSE = "malformed_response"


class ToyopucOperationOutcomeUnknownError(ToyopucError):
    """Raised when a state-changing request may have reached the PLC."""

    def __init__(
        self,
        reason: ToyopucOutcomeUnknownReason,
        message: str,
        *,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.cause = cause
