"""Serializers for user-related operations."""

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

__all__ = ["UserRegistrationSerializer", "UserSerializer"]

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer[User]):
    """Serialize registration request and create a new user."""

    email = serializers.EmailField(
        required=True,
        allow_blank=False,
        allow_null=False,
        help_text=_("A valid email address."),
    )
    password = serializers.CharField(
        required=True,
        allow_blank=False,
        allow_null=False,
        write_only=True,
        style={"input_type": "password"},
        help_text=_("A strong password that meets the complexity requirements."),
    )
    password_confirmation = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        help_text=_("The same password as above, for verification."),
    )

    class Meta:
        """Meta configuration for UserRegistrationSerializer."""

        model = User
        fields = ["email", "password", "password_confirmation"]

    def validate_email(self, value: str) -> str:
        """Validate and normalized email address."""
        return value.lower()

    def validate_password(self, value: str) -> str:
        """Validate password strength."""
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages, code="invalid")

        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate that passwords match and remove confirmation field."""
        if attrs.get("password") != attrs.get("password_confirmation"):
            raise serializers.ValidationError(
                {"password_confirmation": _("Password confirmation does not match")},
                code="invalid",
            )

        attrs.pop("password_confirmation", None)

        return attrs

    def create(self, validated_data: dict[str, Any]) -> User:
        """Create and return a new user instance."""
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer[User]):
    """Serializer for user details requests."""

    class Meta:
        """Meta configuration for UserSerializer."""

        model = User
        fields = ["id", "email", "phone", "first_name", "last_name", "is_active"]
        read_only_fields = ["id", "email", "is_active"]
