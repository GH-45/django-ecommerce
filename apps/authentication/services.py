"""Service module for authentication-related operations."""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import transaction

from .helpers import generate_raw_verification_code
from .models import VerificationCode

__all__ = ["VerificationCodeService"]

logger = logging.getLogger(__name__)

User = get_user_model()


class VerificationCodeService:
    """Service class for managing user verification code."""

    @classmethod
    def create_verification(cls, user: User) -> str:
        """Create a new verification code for the user and invalidate any existing codes.

        Args:
            user: The user for whom to create the verification code.

        Returns:
            str: The raw verification code that was created.
        """
        raw_code = generate_raw_verification_code()

        with transaction.atomic():
            # Deactivate any existing valid codes for the user
            updated_count = VerificationCode.objects.filter(user=user, is_valid=True).update(is_valid=False)
            # Create a new verification code for the user
            VerificationCode.objects.create(user=user, verification_code=make_password(raw_code), is_valid=True)

        logger.info(
            f"Created new verification code. Invalidated {updated_count} previous codes.",
            extra={"user_id": user.id},
        )

        return raw_code

    @classmethod
    def verify_code(cls, user: User, code: str | None = None) -> bool:
        """Verify the provided code for the user.

        If the code is valid, it will be marked as invalid to prevent reuse.

        If the code is invalid, the attempt count will be incremented,
        and if the maximum number of attempts is reached, the code will be marked as invalid.

        Args:
            user: The user for whom to verify the code.
            code: The verification code provided by the user.

        Returns:
            bool: True if the code is valid, otherwise False.
        """
        with transaction.atomic():
            verification = VerificationCode.objects.select_for_update().filter(user=user, is_valid=True).first()

            if not verification or not verification.is_active:
                logger.warning("Verification attempt failed", extra={"user_id": user.id})
                return False

            if check_password(code, verification.verification_code):
                # Mark the verification code as invalid to prevent reuse
                verification.is_valid = False
                verification.save(update_fields=["is_valid"])

                logger.info("Code verified successfully", extra={"user_id": user.id})

                return True

            # On failure, increment the attempt count and check if max attempts have been reached
            verification.attempts += 1

            if verification.max_attempts_reached:
                verification.is_valid = False
                logger.warning("User reached max attempts. Code invalidated.", extra={"user_id": user.id})
            else:
                logger.info(f"Failed verification attempt ({verification.attempts})", extra={"user_id": user.id})

            verification.save(update_fields=["attempts", "is_valid"])

            return False

    # TODO: Temporary implementation, Change for celery task
    @classmethod
    def send_verification_email(cls, user: User) -> bool:
        """Send a verification email to the user with a new verification code.

        Args:
            user: The user to whom the verification email should be sent.
            code: The verification code to provide.

        Returns:
            bool: True if the verification email was sent, otherwise False.
        """
        code = cls.create_verification(user)

        try:
            sent_count = send_mail(
                subject="Email Verification Code",
                message=f"Your verification code is: {code}",
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
