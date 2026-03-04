"""Authentication app URL configurations."""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AccountVerificationView,
    LoginView,
    LogoutView,
    PasswordChangeConfirmView,
    PasswordChangeView,
)

urlpatterns = [
    path("account/verify/", AccountVerificationView.as_view(), name="verify"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("password/change/", PasswordChangeView.as_view(), name="password_change"),
    path("password/change/confirm/", PasswordChangeConfirmView.as_view(), name="password_change_confirm"),
]
