class EmailNotConfiguredError(RuntimeError):
    def __init__(self) -> None:
        super().__init__(
            "Outgoing email is not configured. Set SMTP_HOST, SMTP_USER, "
            "SMTP_PASSWORD and SMTP_FROM in .env."
        )


class MailServerError(RuntimeError):
    """The SMTP server could not be reached or refused the connection."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Could not connect to the mail server: {reason}")


class NoRecipientsError(ValueError):
    def __init__(self) -> None:
        super().__init__("No clients matched the selection, so nothing was sent")
