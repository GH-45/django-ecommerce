"""App settings for authentication app."""

from typing import ClassVar

from django.conf import settings

__all__ = ["verification_code_settings"]


class VerificationCodeSettings:
    """Settings for user verification codes."""

    DEFAULT_CODE_LENGTH: ClassVar[int] = 6
    DEFAULT_CODE_CHARACTERS: ClassVar[str] = "0123456789"
    DEFAULT_MAX_ATTEMPTS: ClassVar[int] = 5
    DEFAULT_EXPIRATION_MINUTES: ClassVar[int] = 7

    @property
    def CODE_LENGTH(self) -> int:
        """Verification code length."""
        return getattr(settings, "VERIFICATION_CODE_LENGTH", self.DEFAULT_CODE_LENGTH)

    @property
    def CODE_CHARACTERS(self) -> str:
        """Verification code allowed characters."""
        return getattr(settings, "VERIFICATION_CODE_CHARACTERS", self.DEFAULT_CODE_CHARACTERS)

    @property
    def MAX_ATTEMPTS(self) -> int:
        """Verification code maximum attempts before locking out."""
        return getattr(settings, "VERIFICATION_CODE_MAX_ATTEMPTS", self.DEFAULT_MAX_ATTEMPTS)

    @property
    def EXPIRATION_MINUTES(self) -> int:
        """Verification code expiration time in minutes."""
        return getattr(settings, "VERIFICATION_CODE_EXPIRATION_MINUTES", self.DEFAULT_EXPIRATION_MINUTES)


verification_code_settings = VerificationCodeSettings()
