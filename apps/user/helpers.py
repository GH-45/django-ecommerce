"""Helper functions for user-related operations."""

from datetime import datetime, timedelta, timezone


def calcule_verification_code_expiration(minutes: int) -> datetime:
    """Calculate the expiration time for an email verification code."""
    return timezone.now() + timedelta(minutes=minutes)
