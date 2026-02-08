"""User and address models for the e-commerce application.

This module contains the custom User model with email-based authentication
and the Address model for managing user billing and shipping addresses.

"""

from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField  # type: ignore[reportMissingTypeStubs]

if TYPE_CHECKING:
    from .models import User


class CustomUserManager(BaseUserManager["User"]):
    """Manager for creating users and superusers with email as the username and required contact fields."""

    def _create_user(self, email: str, password: str | None = None, **extra_fields: Any) -> "User":
        """Create a new User.

        Args:
            email: Email address for the user.
            password: Password for the user. If None, an unusable password is set.
            **extra_fields: Additional fields for the user model.

        Raises:
            ValueError: If email is missing.

        Returns:
            User: The created user instance.

        """
        if not email:
            raise ValueError(_("The Email field cannot be empty"))

        email = self.normalize_email(email).lower()

        user = self.model(email=email, **extra_fields)

        # Set an unusable password if none provided
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)

        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields: Any) -> "User":
        """Create a regular user.

        Args:
            email: Email address for the user.
            password: Password for the user. If None, an unusable password is set.
            **extra_fields: Additional fields for the user model.

        Returns:
            User: The created user instance.

        """
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields: Any) -> "User":
        """Create a superuser.

        Args:
            email: Email address for the user.
            password: Password for the user.
            **extra_fields: Additional fields for the user model.

        Returns:
            User: The created user instance.

        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True"))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True"))
        # Force password for superuser
        if not password:
            raise ValueError(_("Superuser must have a password"))

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model."""

    username = None  # Delete the username field, use email instead

    email = models.EmailField(_("email address"), unique=True, db_index=True)
    phone = PhoneNumberField(_("phone number"), null=True, blank=True, unique=True)
    phone_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        """Metadata configuration for the User model."""

        constraints = [
            UniqueConstraint(Lower("email"), name="unique_email_constraint"),
            UniqueConstraint("phone", name="unique_phone_constraint"),
        ]

    def __str__(self) -> str:
        """Return string representation of the user.

        Returns:
            str: User's full name with email, or just email.

        """
        full_name = self.get_full_name().strip()

        if full_name:
            return f"{full_name} ({self.email})"

        return self.email


class Address(models.Model):
    """Model representing a user's address with billing/shipping type support."""

    class AddressType(models.TextChoices):
        """Enumeration for address types."""

        BILLING = "B", _("Billing")
        SHIPPING = "S", _("Shipping")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")

    country = CountryField(blank_label=_("Select country"))
    first_name = models.CharField(_("first name"), max_length=150, blank=False)
    last_name = models.CharField(_("last name"), max_length=150, blank=False)
    phone = PhoneNumberField(_("phone number"), null=False, blank=False)
    street_1 = models.CharField(_("street and number"), max_length=255, blank=False)
    street_2 = models.CharField(_("additional street information"), max_length=255, blank=True)
    region = models.CharField(_("administrative division"), max_length=100, blank=True)
    city = models.CharField(_("city"), max_length=100, blank=False)
    postal_code = models.CharField(_("postal code"), max_length=20, blank=True)

    address_type = models.CharField(
        _("address type"),
        max_length=1,
        choices=AddressType.choices,
        default=AddressType.SHIPPING,
    )

    default = models.BooleanField(_("default address"), default=False)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        """Metadata configuration for the Address model."""

        verbose_name = _("Address")
        verbose_name_plural = _("Addresses")
        indexes = [models.Index(fields=["user", "address_type"])]
        constraints = [
            UniqueConstraint(
                fields=["user", "address_type"],
                condition=Q(default=True),
                name="unique_default_address_per_user_and_type",
            )
        ]

    def __str__(self) -> str:
        """Return string representation of the address.

        Returns:
            str: Address string with street, city, and country.

        """
        return f"{self.street_1}, {self.city}, {self.country.name}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the address instance.

        If this address is marked as default, unset default on other addresses of the same type for this user.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        """
        if self.default:
            Address.objects.filter(
                user=self.user,
                address_type=self.address_type,
                default=True,
            ).update(default=False)

        super().save(*args, **kwargs)
