from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """Day staff (role=admin) only. Used for sign-off, voiding, reports, settings."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_admin_role)
