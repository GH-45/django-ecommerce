"""App settings for user app."""

from django.conf import settings


class VerificationCodeSettings:
    """Settings for email verification codes."""

    @property
    def CODE_LENGTH(self) -> int:
        """Verification code length."""
        return getattr(settings, "VERIFICATION_CODE_LENGTH", 6)

    @property
    def CODE_CHARACTERS(self) -> str:
        """Verification code allowed characters."""
        return getattr(settings, "VERIFICATION_CODE_CHARACTERS", "0123456789")

    @property
    def MAX_ATTEMPTS(self) -> int:
        """Verification code maximum attempts before locking out."""
        return getattr(settings, "VERIFICATION_CODE_MAX_ATTEMPTS", 5)

    @property
    def EXPIRATION_MINUTES(self) -> int:
        """Verification code expiration time in minutes."""
        return getattr(settings, "VERIFICATION_CODE_EXPIRATION_MINUTES", 7)


verification_code_settings = VerificationCodeSettings()
