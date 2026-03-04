"""Views for authentication-related API endpoints."""

import logging

from django.contrib.auth import update_session_auth_hash
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    AccountVerificationSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordChangeConfirmSerializer,
)
from .services import VerificationCodeService

__all__ = ["AccountVerificationView", "LoginView", "LogoutView", "PasswordChangeView", "PasswordChangeConfirmView"]

logger = logging.getLogger(__name__)


class AccountVerificationView(APIView):
    """API view to handle user account verification."""

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        """Handle POST request to verify user account."""
        serializer = AccountVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Activate the user account
        user = serializer.validated_data.get("user")
        user.is_active = True
        user.save(update_fields=["is_active"])

        # Generate JWT token for the user
        refresh = RefreshToken.for_user(user)

        logger.info("User account verified successfully", extra={"user_id": user.id})

        return Response(
            {
                "message": "Account verified successfully",
                "token": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_200_OK,
        )


class LoginView(APIView):
    """API view to handle user login."""

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        """Handle POST request to authenticate user."""
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        # Recover the authenticated user
        user = serializer.validated_data.get("user")

        # Generate JWT token for the user
        refresh = RefreshToken.for_user(user)

        logger.info("User logged in successfully", extra={"user_id": user.id})

        return Response(
            {
                "message": "Login successful",
                "token": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """API view to handle user logout."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        """Handle POST request to log out user."""
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Blacklist the refresh token to log out the user
        token = serializer.validated_data.get("token")
        token.blacklist()

        logger.info("User logged out successfully", extra={"user_id": request.user.id})

        return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)


class PasswordChangeView(APIView):
    """API view to handle password change requests."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    throttle_scope = "send_verification_code"

    def post(self, request: Request) -> Response:
        """Handler POST request to change user password."""
        VerificationCodeService.send_verification_email(request.user)

        logger.info("Verification email scheduled to be sent", extra={"user_id": request.user.id})

        return Response(
            {"message": "Verification code sent successfully. Please check your email"},
            status=status.HTTP_200_OK,
        )


class PasswordChangeConfirmView(APIView):
    """API view to handle password change confirmation requests."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        """Handler POST request to confirm password change."""
        serializer = PasswordChangeConfirmSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        # Update the user password
        user = request.user
        user.set_password(serializer.validated_data.get("new_password"))
        user.save()

        logger.info("Password changed successfully", extra={"user_id": user.id})

        # Keep the user authenticated after password change
        update_session_auth_hash(request, user)

        # Blacklist all existing refresh tokens for the user to force re-authentication with the new password
        for token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=token)

        # Generate new JWT token for the user
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Password changed successfully",
                "token": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_200_OK,
        )
