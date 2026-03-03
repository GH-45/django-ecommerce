"""Helper functions for user-related operations."""

from datetime import datetime, timedelta

from django.utils import timezone
from django.utils.crypto import get_random_string

from .conf import verification_code_settings

__all__ = ["calcule_verification_code_expiration", "generate_raw_verification_code"]


def calcule_verification_code_expiration(minutes: int) -> datetime:
    """Calculate the expiration time for a verification code."""
    return timezone.now() + timedelta(minutes=minutes)


def generate_raw_verification_code() -> str:
    """Generate a random string to be used as a verification code.

    The generated code will have a length and character set defined in the verification_code_settings.
    """
    return get_random_string(
        length=verification_code_settings.CODE_LENGTH,
        allowed_chars=verification_code_settings.CODE_CHARACTERS,
    )
