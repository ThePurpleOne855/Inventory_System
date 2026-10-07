"""Runtime configuration for invoicing, outgoing mail, and CORS.

Operator credentials live in .env.auth and are handled by app.core.auth.
"""
import os

from dotenv import load_dotenv

load_dotenv()


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _get_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc


def _get_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    # --- Browser clients allowed to call the API ---
    @property
    def cors_origins(self) -> list[str]:
        raw = _get("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    # --- Company details, printed on invoices ---
    company_name: str = _get("COMPANY_NAME", "Madre Tierra")
    company_address: str = _get("COMPANY_ADDRESS", "")
    company_email: str = _get("COMPANY_EMAIL", "")
    company_phone: str = _get("COMPANY_PHONE", "")
    currency: str = _get("CURRENCY", "$")

    # --- Outgoing email (SMTP) ---
    smtp_host: str = _get("SMTP_HOST", "")
    smtp_port: int = _get_int("SMTP_PORT", 587)
    smtp_user: str = _get("SMTP_USER", "")
    smtp_password: str = _get("SMTP_PASSWORD", "")
    smtp_starttls: bool = _get_bool("SMTP_STARTTLS", True)
    smtp_from: str = _get("SMTP_FROM", "")

    @property
    def mail_from(self) -> str:
        return self.smtp_from or self.smtp_user

    @property
    def email_configured(self) -> bool:
        return bool(self.smtp_host and self.mail_from)


settings = Settings()
