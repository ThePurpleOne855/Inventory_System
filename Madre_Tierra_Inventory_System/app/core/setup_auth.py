"""Run with python -m app.core.setup_auth to configure the single operator."""
import argparse
import getpass
import os
from pathlib import Path

from dotenv import set_key

from app.core.security import hash_password

AUTH_FILE = Path(__file__).resolve().parents[3] / ".env.auth"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replace", action="store_true", help="Replace credentials and invalidate existing sessions after restart")
    args = parser.parse_args()
    if AUTH_FILE.exists() and not args.replace:
        parser.error(".env.auth already exists; use --replace to rotate credentials")
    username = input("Operator username [admin]: ").strip() or "admin"
    if len(username) > 128:
        parser.error("Username must contain at most 128 characters")
    password = getpass.getpass("Password (at least 12 characters): ")
    if not 12 <= len(password) <= 1024:
        parser.error("Password must contain 12 to 1024 characters")
    if password != getpass.getpass("Confirm password: "):
        parser.error("Passwords do not match")
    password_hash = hash_password(password)
    flags = os.O_WRONLY | os.O_CREAT | (os.O_TRUNC if args.replace else os.O_EXCL)
    with os.fdopen(os.open(AUTH_FILE, flags, 0o600), "w"):
        pass
    os.chmod(AUTH_FILE, 0o600)
    set_key(str(AUTH_FILE), "AUTH_USERNAME", username)
    set_key(str(AUTH_FILE), "AUTH_PASSWORD_HASH", password_hash)
    print("Operator credentials saved to .env.auth. Restart the API to load them.")


if __name__ == "__main__":
    main()
