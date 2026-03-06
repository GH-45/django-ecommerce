"""Service module for authentication-related operations."""

import logging
from uuid import UUID

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from .helpers import generate_raw_verification_code
from .models import VerificationCode

__all__ = ["VerificationCodeService"]

logger = logging.getLogger(__name__)

User = get_user_model()


class VerificationSubject(models.TextChoices):
    """Subjects for verification emails based on purpose."""

    ACCOUNT_VERIFICATION = "ACCOUNT_VERIFICATION", _("Account Verification")
    MFA_AUTHENTICATION = "MFA_AUTHENTICATION", _("Multi-factor Authentication Code")
    EMAIL_CHANGE = "EMAIL_CHANGE", _("Email Change Confirmation")
    PASSWORD_CHANGE = "PASSWORD_CHANGE", _("Password Change Notification")
    PASSWORD_RESET = "PASSWORD_RESET", _("Password Reset Notification")
    DEFAULT = "DEFAULT", _("Verification Code")


class VerificationCodeService:
    """Service class for managing user verification code."""

    @classmethod
    def create_verification(cls, user: User, purpose: VerificationCode.VerificationType) -> tuple[str, UUID]:
        """Create a new verification code for the user and invalidate any existing codes.

        Args:
            user: The user for whom to create the verification code.
            purpose: The purpose of the verification code.

        Returns:
            str: The raw verification code that was created.
        """
        raw_code = generate_raw_verification_code()

        with transaction.atomic():
            # Deactivate any existing valid codes for the user (For the same purpose only)
            updated_count = VerificationCode.objects.filter(
                user=user,
                purpose=purpose,
                is_valid=True,
            ).update(is_valid=False)

            # Create a new verification code for the user
            verification = VerificationCode.objects.create(
                user=user,
                purpose=purpose,
                verification_code=make_password(raw_code),
                is_valid=True,
            )

        logger.info(
            f"Created new verification code. Invalidated {updated_count} previous codes.",
            extra={"user_id": user.id, "purpose": purpose},
        )

        return raw_code, verification.verification_token

    @classmethod
    def verify_code(
        cls,
        email: str,
        verification_code: str,
        verification_token: UUID,
        purpose: VerificationCode.VerificationType,
    ) -> bool:
        """Verify the provided code for the user.

        If the code is valid, it will be marked as invalid to prevent reuse.

        If the code is invalid, the attempt count will be incremented,
        and if the maximum number of attempts is reached, the code will be marked as invalid.

        Args:
            email: The user email address for whom to verify the code.
            verification_code: The verification code provided to the user.
            verification_token: The verification token provided to the user.
            purpose: The purpose of the verification code.

        Returns:
            bool: True if the code is valid, otherwise False.
        """
        with transaction.atomic():
            verification = (
                VerificationCode.objects.select_for_update()
                .filter(verification_token=verification_token, user__email=email, purpose=purpose, is_valid=True)
                .first()
            )

            if not verification or not verification.is_active:
                logger.warning("Verification attempt failed", extra={"token": verification_token, "purpose": purpose})
                return False

            if check_password(verification_code, verification.verification_code):
                # Mark the verification code as invalid to prevent reuse
                verification.is_valid = False
                verification.save(update_fields=["is_valid"])

                logger.info("Code verified successfully", extra={"token": verification_token, "purpose": purpose})

                return True

            # On failure, increment the attempt count and check if max attempts have been reached
            verification.attempts += 1
            if verification.max_attempts_reached:
                verification.is_valid = False
                logger.warning(
                    "Max attempts reached. Code invalidated.",
                    extra={"token": verification_token, "purpose": purpose},
                )

            verification.save(update_fields=["attempts", "is_valid"])

            return False

    # TODO: Temporary implementation, Change for celery task
    @classmethod
    def send_verification_email(cls, user: User, purpose: VerificationCode.VerificationType) -> bool:
        """Send a verification email to the user with a new verification code.

        Args:
            user: The user to whom the verification email should be sent.
            purpose: The verification code to provide.

        Returns:
            bool: True if the verification email was sent, otherwise False.
        """
        verification_code, verification_token = cls.create_verification(user, purpose)
        verification_url = verification_token

        try:
            sent_count = send_mail(
                subject=getattr(VerificationSubject, purpose.value, VerificationSubject.DEFAULT),
                message=(
                    f"Your verification code is: {verification_code}\r\n"
                    f"Access the following link to enter your code: {verification_url}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

            if sent_count > 0:
                logger.info("Verification email sent", extra={"user_id": user.id})
                return True

            logger.warning("Mail backend returned 0 sent messages", extra={"user_id": user.id})

            return False

        except Exception:
            logger.exception("Failed to send verification email", extra={"user_id": user.id})
            return False
