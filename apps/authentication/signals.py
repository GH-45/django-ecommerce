"""Signals for authentication-related events."""

from typing import Any

from django.contrib.auth import get_user_model
from django.dispatch import receiver

from apps.user.signals import user_registered

from .models import VerificationCode
from .services import VerificationCodeService

User = get_user_model()


@receiver(user_registered)
def handle_user_registration(sender: str, user: User, **kwargs: Any) -> None:
    """Handle user registration event."""
    VerificationCodeService.send_verification_email(user, VerificationCode.VerificationType.ACCOUNT_VERIFICATION)
