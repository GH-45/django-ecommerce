"""User app URL configurations."""

from django.urls import path

from .views import UserDetailView, UserListView, UserProfileView, UserRegistrationView

urlpatterns = [
    path("register/", UserRegistrationView.as_view(), name="register"),
    path("me/", UserProfileView.as_view(), name="user_profile"),
    # Admin-only endpoints
    path("", UserListView.as_view(), name="user_list"),
    path("<int:id>/", UserDetailView.as_view(), name="user_detail"),
]
