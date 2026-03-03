"""Views for user-related API endpoints."""

import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import UserRegistrationSerializer, UserSerializer
from .signals import user_registered

__all__ = ["UserRegistrationView", "UserProfileView", "UserDetailView", "UserListView"]

logger = logging.getLogger(__name__)

User = get_user_model()


class UserRegistrationView(APIView):
    """API view to handle user registration."""

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        """Handle POST request to register a new user."""
        serializer = UserRegistrationSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data.get("email")

        try:
            with transaction.atomic():
                # Check if a user with the same email already exists (case-insensitive)
                existing_user = User.objects.filter(email=email).first()

                # If already exists, suppress error and log the attempt without creating a new user
                if existing_user:
                    logger.info("User with email already exists", extra={"user_id": existing_user.id})

                # If not exists, create a new user and send verification email
                else:
                    # Create inactive user
                    user = serializer.save(is_active=False)
                    logger.info("New user registered", extra={"user_id": user.id})

                    # Send user verification code via email to activate the account
                    transaction.on_commit(lambda: user_registered.send(sender=self.__class__, user=user))
                    logger.info("Verification email scheduled to be sent", extra={"user_id": user.id})

            return Response(
                {"message": "Verification code sent successfully. Please check your email"},
                status=status.HTTP_201_CREATED,
            )

        except Exception:
            logger.exception("Error during user registration")
            return Response(
                {"detail": "An error occurred during registration. Please try again later"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserProfileView(RetrieveUpdateAPIView[User]):
    """API view to retrieve and update user profile."""

    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self) -> User:
        """Return the authenticated user."""
        return self.request.user


class UserDetailView(RetrieveAPIView[User]):
    """API view to retrieve user details."""

    permission_classes = [IsAdminUser]
    serializer_class = UserSerializer
    queryset = User.objects.all()
    lookup_field = "id"


class UserListView(ListAPIView[User]):
    """API view to list all users."""

    permission_classes = [IsAdminUser]
    serializer_class = UserSerializer
    queryset = User.objects.all()
    lookup_field = "id"
