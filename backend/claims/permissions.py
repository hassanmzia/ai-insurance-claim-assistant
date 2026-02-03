"""Custom permission classes for Role-Based Access Control (RBAC)."""
from rest_framework import permissions


def _get_role(user):
    """Get the role from user's profile, defaulting to 'customer'."""
    profile = getattr(user, 'profile', None)
    return profile.role if profile else 'customer'


class IsAdmin(permissions.BasePermission):
    """Only administrators can access."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and _get_role(request.user) == 'admin'


class IsAdminOrAdjuster(permissions.BasePermission):
    """Administrators and adjusters can access."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and _get_role(request.user) in ('admin', 'adjuster')


class IsStaff(permissions.BasePermission):
    """Admin, adjuster, and reviewer roles can access."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and _get_role(request.user) in ('admin', 'adjuster', 'reviewer')


class IsAdminOrReadOnly(permissions.BasePermission):
    """Admin gets full access; others get read-only."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return _get_role(request.user) == 'admin'


class IsStaffOrReadOnly(permissions.BasePermission):
    """Staff (admin/adjuster/reviewer) gets full access; customers read-only."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return _get_role(request.user) in ('admin', 'adjuster', 'reviewer')


class IsOwnerOrStaff(permissions.BasePermission):
    """Object owner or staff can access."""
    def has_object_permission(self, request, view, obj):
        if _get_role(request.user) in ('admin', 'adjuster', 'reviewer'):
            return True
        # Check various ownership patterns
        if hasattr(obj, 'claimant') and obj.claimant == request.user:
            return True
        if hasattr(obj, 'holder') and obj.holder == request.user:
            return True
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        return False


class CanProcessClaims(permissions.BasePermission):
    """Only admin and adjuster can process/update claims."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and _get_role(request.user) in ('admin', 'adjuster')


class CanManageFraudAlerts(permissions.BasePermission):
    """Admin, adjuster, reviewer can view; only admin/adjuster can resolve."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        role = _get_role(request.user)
        if request.method in permissions.SAFE_METHODS:
            return role in ('admin', 'adjuster', 'reviewer')
        return role in ('admin', 'adjuster')
