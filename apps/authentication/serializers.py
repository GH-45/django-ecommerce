"""Serializers for authentication-related operations."""

from typing import Any

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import VerificationCode
from .services import VerificationCodeService

__all__ = ["AccountVerificationSerializer", "LoginSerializer", "LogoutSerializer", "PasswordChangeConfirmSerializer"]

User = get_user_model()


class AccountVerificationSerializer(serializers.Serializer[Any]):
    """Serialize account verification request."""

    email = serializers.EmailField(
        required=True,
        allow_blank=False,
        allow_null=False,
        write_only=True,
        help_text=_("The email address associated with the account to verify."),
    )
    code = serializers.CharField(
        required=True,
        allow_blank=False,
        allow_null=False,
        write_only=True,
        help_text=_("The verification code sent to the user."),
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate the provider verification code for the user."""
        validated = VerificationCodeService.verify_code(
            email=attrs.get("email"),
            verification_code=attrs.get("code"),
            verification_token=self.context.get("verification_token"),
            purpose=VerificationCode.VerificationType.ACCOUNT_VERIFICATION,
        )

        if not validated:
            raise serializers.ValidationError(
                _("Unable to validate account, verify the email address and verification code"),
                code="verification_code_error",
            )

        return attrs


class LoginSerializer(serializers.Serializer[Any]):
    """Serialize account login request."""

    email = serializers.EmailField(
        required=True,
        allow_blank=False,
        allow_null=False,
        write_only=True,
        help_text=_("The email address associated with an account."),
    )
    password = serializers.CharField(
        required=True,
        allow_blank=False,
        allow_null=False,
        write_only=True,
        style={"input_type": "password"},
        help_text=_("The password for the account."),
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Authenticate user with provided credentials."""
        user = authenticate(
            request=self.context.get("request"),
            email=attrs.get("email"),
            password=attrs.get("password"),
        )

        if not user or not user.is_active:
            raise serializers.ValidationError(
                _("Unable to log in with provided credentials, please verify your email and password"),
                code="authentication_error",
            )

        attrs["user"] = user

        return attrs


class LogoutSerializer(serializers.Serializer[Any]):
    """Serialize account logout request."""

    refresh = serializers.CharField(
        required=True,
        allow_blank=False,
        allow_null=False,
        write_only=True,
        help_text=_("The refresh token to be blacklisted."),
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate refresh token."""
        try:
            attrs["token"] = RefreshToken(attrs["refresh"])
        except (TokenError, KeyError):
            raise serializers.ValidationError({"refresh": _("Invalid or expired token")}, code="invalid_token")

        return attrs


class PasswordChangeConfirmSerializer(serializers.Serializer[Any]):
    """Serialize password change request."""

    old_password = serializers.CharField(
        required=True,
        allow_blank=False,
        allow_null=False,
        write_only=True,
        style={"input_type": "password"},
        help_text=_("The current password for the account."),
    )
    new_password = serializers.CharField(
        required=True,
        allow_blank=False,
        allow_null=False,
        write_only=True,
        style={"input_type": "password"},
        validators=[validate_password],
        help_text=_("The new password for the account."),
    )
    new_password_confirmation = serializers.CharField(
        required=True,
        allow_blank=False,
        allow_null=False,
        write_only=True,
        style={"input_type": "password"},
        help_text=_("The same new password as above, for verification."),
    )
    code = serializers.CharField(
        required=True,
        allow_blank=False,
        allow_null=False,
        write_only=True,
        help_text=_("The verification code sent to the user."),
    )

    def validate_old_password(self, value: str) -> str:
        """Validate that the provided current password is correct."""
        user = self.context["request"].user

        if not user.check_password(value):
            raise serializers.ValidationError(
                {"old_password": _("Current password is incorrect")},
                code="invalid_password",
            )

        return value

    def validate_code(self, value: str) -> str:
        """Validate the provided verification code."""
        user = self.context["request"].user

        if not VerificationCodeService.verify_code(
            email=user.email,
            verification_code=value,
            verification_token=self.context.get("verification_token"),
            purpose=VerificationCode.VerificationType.PASSWORD_CHANGE,
        ):
            raise serializers.ValidationError(
                {"code": _("Invalid verification code")},
                code="verification_code_error",
            )

        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate new password assignment and confirmation."""
        # Ensure new password is different from the current password
        if attrs.get("new_password") == attrs.get("old_password"):
            raise serializers.ValidationError(
                {"new_password": _("New password must be different from the current password")},
                code="invalid_new_password",
            )

        # Validate that new password and confirmation match
        if attrs.get("new_password") != attrs.get("new_password_confirmation"):
            raise serializers.ValidationError(
                {"new_password_confirmation": _("Password confirmation does not match")},
                code="invalid_confirmation_password",
            )

        attrs.pop("new_password_confirmation", None)

        return attrs
