"""Model to authentication-related data."""

from collections.abc import Callable
from functools import partial

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .conf import verification_code_settings
from .helpers import calcule_verification_code_expiration


class VerificationCode(models.Model):
    """Model to store user verification codes."""

    class VerificationStatus(models.TextChoices):
        """Enumeration for verification code status."""

        ACTIVE = "ACTIVE", _("Active")
        INACTIVE = "INACTIVE", _("Inactive")
        EXPIRED = "EXPIRED", _("Expired")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="verification_codes")

    verification_code = models.CharField(_("verification code"), max_length=128)
    attempts = models.IntegerField(_("attempts"), default=0)
    is_valid = models.BooleanField(_("is valid"), default=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    expires_at = models.DateTimeField(
        _("expires at"),
        default=partial(calcule_verification_code_expiration, minutes=verification_code_settings.EXPIRATION_MINUTES),
    )

    class Meta:
        """Metadata configuration for the Verification Code model."""

        verbose_name = _("Verification Code")
        verbose_name_plural = _("Verification Codes")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_valid", "-created_at"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        """Return string representation of the user verification code.

        Returns:
            str: String showing the user's email and verification validity status.
        """
        return f"Code for {self.user_id or 'Unknown User'} (Status: {self.status})"

    @property
    def status(self) -> VerificationStatus:
        """Return the status of the verification code."""
        status_rules: dict[VerificationCode.VerificationStatus, Callable[[], bool]] = {
            self.VerificationStatus.INACTIVE: lambda: not self.is_valid or self.max_attempts_reached,
            self.VerificationStatus.EXPIRED: lambda: self.is_expired,
            self.VerificationStatus.ACTIVE: lambda: True,  # Default to active if not inactive or expired
        }

        return next((status for status, rule in status_rules.items() if rule()))

    @property
    def is_active(self) -> bool:
        """Check if the verification code is active for use."""
        return self.status == self.VerificationStatus.ACTIVE

    @property
    def is_expired(self) -> bool:
        """Check if the verification code has expired."""
        return self.expires_at and self.expires_at <= timezone.now()

    @property
    def max_attempts_reached(self) -> bool:
        """Check if the maximum number of verification attempts has been reached."""
        return self.attempts >= verification_code_settings.MAX_ATTEMPTS
