from __future__ import annotations

from django.http import Http404
from mongoengine.queryset.visitor import Q
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_service import services
from auth_service.constants import LEVEL_ADMIN, LEVEL_CUSTOMER, LEVEL_MOD, LEVEL_ROOT, STATUS_ACTIVE, STATUS_BANNED
from auth_service.models import User
from auth_service.permissions import PrincipalRequired, ensure_level, ensure_perm
from auth_service.rbac import ensure_level_hierarchy, get_user_permissions
from auth_service.serializers import (
    UserAdminCreateSerializer,
    UserAdminUpdateSerializer,
    UserGroupAssignSerializer,
    UserMeUpdateSerializer,
    serialize_user,
)
from auth_service.views.auth_api import LoginView, RegisterView


def _get_user_or_404(user_id: str) -> User:
    user = services.get_user_by_id(user_id)
    if not user:
        raise Http404("User not found")
    return user


class UserMeView(APIView):
    permission_classes = [PrincipalRequired]

    def get(self, request):
        user = _get_user_or_404(request.principal.user_id)
        perms = get_user_permissions(user)
        return Response({"ok": True, "user": serialize_user(user, perms), "perms": sorted(perms)})

    def patch(self, request):
        serializer = UserMeUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = _get_user_or_404(request.principal.user_id)
        data = serializer.validated_data
        email = data.get("email")
        phone = data.get("phone")
        if email or phone:
            services.ensure_unique_contact(email=email, phone=phone, exclude_id=str(user.id))
        services.update_user(
            user,
            fullName=data.get("fullName") or user.fullName,
            email=email or user.email,
            phone=phone or user.phone,
        )
        return Response({"ok": True, "user": serialize_user(user)})


class UserCollectionView(APIView):
    permission_classes = [PrincipalRequired]

    def get(self, request):
        principal = request.principal
        ensure_level(principal, LEVEL_MOD)
        ensure_perm(principal, "user.list")
        q = request.query_params.get("q")
        level = request.query_params.get("level")
        status_filter = request.query_params.get("status")
        page = max(int(request.query_params.get("page", 1)), 1)
        page_size = min(max(int(request.query_params.get("pageSize", 20)), 1), 100)

        queryset = User.objects
        if q:
            queryset = queryset.filter(
                Q(fullName__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
            )
        if level:
            queryset = queryset.filter(level=level)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        total = queryset.count()
        users = list(queryset.skip((page - 1) * page_size).limit(page_size))
        return Response(
            {
                "ok": True,
                "data": [serialize_user(user) for user in users],
                "page": page,
                "pageSize": page_size,
                "total": total,
            }
        )

    def post(self, request):
        principal = request.principal
        ensure_perm(principal, "user.create")
        serializer = UserAdminCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        groups = [code.upper() for code in data.get("groups", [])]
        if groups:
            services.ensure_groups_exist(groups)
        target_level = data.get("level", LEVEL_CUSTOMER)
        ensure_level_hierarchy(principal, target_level)
        user = services.create_user(
            email=data.get("email"),
            phone=data.get("phone"),
            full_name=data["fullName"],
            password=data["password"],
            level=target_level,
            status=data.get("status", STATUS_ACTIVE),
            groups=groups,
            extra_perms=data.get("extraPerms", []),
        )
        return Response({"ok": True, "user": serialize_user(user)})


class UserDetailView(APIView):
    permission_classes = [PrincipalRequired]

    def get(self, request, user_id: str):
        principal = request.principal
        ensure_perm(principal, "user.read")
        user = _get_user_or_404(user_id)
        perms = get_user_permissions(user)
        return Response({"ok": True, "user": serialize_user(user, perms), "perms": sorted(perms)})

    def patch(self, request, user_id: str):
        principal = request.principal
        ensure_perm(principal, "user.update")
        serializer = UserAdminUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = _get_user_or_404(user_id)
        data = serializer.validated_data
        if "level" in data:
            ensure_level_hierarchy(principal, data["level"])
        if "email" in data or "phone" in data:
            services.ensure_unique_contact(
                email=data.get("email"),
                phone=data.get("phone"),
                exclude_id=str(user.id),
            )
        if "groups" in data:
            services.ensure_groups_exist([code.upper() for code in data["groups"]])
        services.update_user(
            user,
            email=data.get("email"),
            phone=data.get("phone"),
            fullName=data.get("fullName"),
            level=data.get("level"),
            status=data.get("status"),
            groups=[code.upper() for code in data.get("groups", user.groups)],
            extraPerms=data.get("extraPerms", user.extraPerms),
        )
        return Response({"ok": True, "user": serialize_user(user)})


class UserStatusView(APIView):
    permission_classes = [PrincipalRequired]

    def post(self, request, user_id: str, target_status: str):
        principal = request.principal
        ensure_perm(principal, "user.update")
        user = _get_user_or_404(user_id)
        if user.level == LEVEL_ROOT and principal.level != LEVEL_ROOT:
            return Response({"ok": False, "error": "Cannot modify Root"}, status=403)
        user.status = target_status
        user.save()
        return Response({"ok": True, "user": serialize_user(user)})


class UserLevelView(APIView):
    permission_classes = [PrincipalRequired]

    def post(self, request, user_id: str):
        principal = request.principal
        ensure_perm(principal, "user.role.set")
        user = _get_user_or_404(user_id)
        new_level = request.data.get("level")
        if not new_level:
            return Response({"ok": False, "error": "level required"}, status=400)
        if new_level == LEVEL_ROOT and principal.level != LEVEL_ROOT:
            return Response({"ok": False, "error": "Cannot assign Root"}, status=403)
        ensure_level_hierarchy(principal, new_level)
        user.level = new_level
        user.save()
        return Response({"ok": True, "user": serialize_user(user)})


class UserGroupAssignView(APIView):
    permission_classes = [PrincipalRequired]

    def post(self, request, user_id: str):
        principal = request.principal
        ensure_level(principal, LEVEL_ADMIN)
        ensure_perm(principal, "user.update")
        serializer = UserGroupAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        groups = [code.upper() for code in serializer.validated_data["groups"]]
        services.ensure_groups_exist(groups)
        user = _get_user_or_404(user_id)
        user.groups = groups
        user.save()
        return Response({"ok": True, "user": serialize_user(user)})


class LegacyUserLoginView(LoginView):
    pass


class LegacyUserRegisterView(RegisterView):
    pass
