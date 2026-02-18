from __future__ import annotations

from django.http import Http404
from mongoengine.errors import NotUniqueError
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_service.models import GroupPermission, UserGroup
from auth_service.permissions import PrincipalRequired, ensure_perm
from auth_service.serializers import GroupPermsSerializer, GroupSerializer


def _code_from_path(code: str) -> str:
    return code.strip().upper()


def _get_group_or_404(code: str) -> UserGroup:
    group = UserGroup.objects(code=code).first()
    if not group:
        raise Http404("Group not found")
    return group


class GroupCollectionView(APIView):
    permission_classes = [PrincipalRequired]

    def get(self, request):
        ensure_perm(request.principal, "group.list")
        groups = UserGroup.objects.order_by("code")
        data = [
            {
                "code": group.code,
                "name": group.name,
                "description": group.description,
                "status": group.status,
                "createdAt": group.createdAt.isoformat() if group.createdAt else None,
                "updatedAt": group.updatedAt.isoformat() if group.updatedAt else None,
            }
            for group in groups
        ]
        return Response({"ok": True, "data": data})

    def post(self, request):
        ensure_perm(request.principal, "group.create")
        serializer = GroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        payload["code"] = payload["code"].upper()
        group = UserGroup(**payload)
        group.save()
        return Response({"ok": True, "group": payload})


class GroupDetailView(APIView):
    permission_classes = [PrincipalRequired]

    def get(self, request, code: str):
        ensure_perm(request.principal, "group.read")
        group = _get_group_or_404(_code_from_path(code))
        perms = [perm.perm for perm in GroupPermission.objects(groupCode=group.code)]
        return Response({
            "ok": True,
            "group": {
                "code": group.code,
                "name": group.name,
                "description": group.description,
                "status": group.status,
                "perms": perms,
            },
        })

    def patch(self, request, code: str):
        ensure_perm(request.principal, "group.update")
        serializer = GroupSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        group = _get_group_or_404(_code_from_path(code))
        data = serializer.validated_data
        for field in ("name", "description", "status"):
            if field in data:
                setattr(group, field, data[field])
        group.save()
        return Response({"ok": True})

    def delete(self, request, code: str):
        ensure_perm(request.principal, "group.delete")
        group = _get_group_or_404(_code_from_path(code))
        GroupPermission.objects(groupCode=group.code).delete()
        group.delete()
        return Response({"ok": True})


class GroupPermissionView(APIView):
    permission_classes = [PrincipalRequired]

    def get(self, request, code: str):
        ensure_perm(request.principal, "group.read")
        group_code = _code_from_path(code)
        perms = [perm.perm for perm in GroupPermission.objects(groupCode=group_code)]
        return Response({"ok": True, "perms": perms})

    def post(self, request, code: str):
        ensure_perm(request.principal, "group.perm.set")
        serializer = GroupPermsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group_code = _code_from_path(code)
        _get_group_or_404(group_code)
        data = serializer.validated_data
        for perm in data.get("permsAdd", []):
            try:
                GroupPermission(groupCode=group_code, perm=perm).save()
            except NotUniqueError:
                continue
        if data.get("permsRemove"):
            GroupPermission.objects(groupCode=group_code, perm__in=data["permsRemove"]).delete()
        perms = [perm.perm for perm in GroupPermission.objects(groupCode=group_code)]
        return Response({"ok": True, "perms": perms})