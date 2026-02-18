from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):  # pragma: no cover - simple health endpoint
        return Response({"status": "ok"})
