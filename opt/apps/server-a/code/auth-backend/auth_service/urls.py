from django.urls import path

from auth_service.constants import STATUS_ACTIVE, STATUS_BANNED
from auth_service.views import auth_api, group_api, health, oauth_api, user_api

urlpatterns = [
    path("health", health.health_view, name="prefixed-health"),
    path("v1/auth/register", auth_api.RegisterView.as_view()),
    path("v1/auth/login", auth_api.LoginView.as_view()),
    path("v1/auth/logout", auth_api.LogoutView.as_view()),
    path("v1/auth/forgot-password", auth_api.ForgotPasswordView.as_view()),
    path("v1/auth/reset-password", auth_api.ResetPasswordView.as_view()),
    path("v1/auth/change-password", auth_api.ChangePasswordView.as_view()),
    path("v1/auth/introspect", auth_api.IntrospectView.as_view()),
    path("v1/users/me", user_api.UserMeView.as_view()),
    path("v1/users", user_api.UserCollectionView.as_view()),
    path("v1/users/<str:user_id>", user_api.UserDetailView.as_view()),
    path("v1/users/<str:user_id>/ban", user_api.UserStatusView.as_view(), {"target_status": STATUS_BANNED}),
    path("v1/users/<str:user_id>/activate", user_api.UserStatusView.as_view(), {"target_status": STATUS_ACTIVE}),
    path("v1/users/<str:user_id>/set-level", user_api.UserLevelView.as_view()),
    path("v1/users/<str:user_id>/groups", user_api.UserGroupAssignView.as_view()),
    path("v1/groups", group_api.GroupCollectionView.as_view()),
    path("v1/groups/<str:code>", group_api.GroupDetailView.as_view()),
    path("v1/groups/<str:code>/perms", group_api.GroupPermissionView.as_view()),
    path("v1/oauth/google/start", oauth_api.GoogleOAuthStart.as_view(), name="oauth-google-start"),
    path("v1/oauth/google/callback", oauth_api.GoogleOAuthCallback.as_view(), name="oauth-google-callback"),
    path("v1/oauth/microsoft/start", oauth_api.MicrosoftOAuthStart.as_view(), name="oauth-microsoft-start"),
    path("v1/oauth/microsoft/callback", oauth_api.MicrosoftOAuthCallback.as_view(), name="oauth-microsoft-callback"),
    path("user/login", user_api.LegacyUserLoginView.as_view()),
    path("user/register", user_api.LegacyUserRegisterView.as_view()),
]
