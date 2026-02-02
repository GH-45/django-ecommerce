from typing import TYPE_CHECKING, Any

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models

if TYPE_CHECKING:
    from .models import User


class CustomUserManager(BaseUserManager["User"]):
    def _create_user(self, email: str, username: str, password: str | None = None, **extra_fields: Any) -> "User":
        if not email:
            raise ValueError("Invalid user email address")
        if not username:
            raise ValueError("Invalid user username")

        user = self.model(email=self.normalize_email(email), username=username, **extra_fields)

        # Set an unusable password if none provided
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)

        return user

    def create_user(self, email: str, username: str, password: str | None = None, **extra_fields: Any) -> "User":
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", True)

        return self._create_user(email, username, password, **extra_fields)

    def create_superuser(self, email: str, username: str, password: str | None = None, **extra_fields: Any) -> "User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        if not password:
            raise ValueError("Superuser must have a password.")

        return self._create_user(email, username, password, **extra_fields)


class User(AbstractUser):
    username_validator = UnicodeUsernameValidator()

    username = models.CharField(
        "username",
        max_length=150,
        db_index=True,
        unique=True,
        validators=[username_validator],
        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
    )
    email = models.EmailField("email address", db_index=True, unique=True)
    is_staff = models.BooleanField("staff status", default=False)
    is_active = models.BooleanField("active", default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = CustomUserManager()

    def __str__(self) -> str:
        return self.username

    def get_short_name(self) -> str:
        return self.username

    def get_full_name(self) -> str:
        return self.username

    def clean(self) -> None:
        super().clean()
        # Enforce case-insensitive uniqueness of email addresses
        if self.email:
            self.email = self.email.strip().lower()
